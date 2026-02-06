import asyncio
from typing import List, Tuple
from tqdm.asyncio import tqdm
from src.tools.hn_adapter import HackerNewsAdapter
from src.tools.rss_adapter import RSSAdapter
from src.tools.reddit_adapter import RedditAdapter
from src.tools.evaluator import EvaluatorFactory
from src.models.items import IngestedItem, EvaluationResult
from src.services.database import db
from src.services.llm import llm
from src.services.logger import logger
from src.services.vector_store import vector_store
from src.config import settings
from src.tools.prefilter import prefilter
from datetime import datetime
import json

class Pipeline:
    def __init__(self):
        self.hn_adapter = HackerNewsAdapter()
        self.rss_adapter = RSSAdapter()
        self.reddit_adapter = RedditAdapter()
    
    async def run_pipeline(self, summary_mode: bool = False):
        """
        Main entry point. 
        In the new RAG architecture, this orchestrates:
        1. Ingestion (Scrape -> Save)
        2. Generation (Query -> Evaluate -> Send)
        """
        await db.init()
        
        # Phase 1: Ingestion
        await self.run_ingestion()
        
        # Phase 2: Generation
        await self.run_generation(summary_mode)

    async def run_ingestion(self):
        logger.info("Phase 1: Ingestion Started")
        
        # 1. Fetch
        # 1. Fetch
        print("Fetching content from sources...")
        
        # Load Source Preferences
        use_hn = (await db.get_preference("SOURCE_HN_ENABLED", "true")).lower() == "true"
        use_reddit = (await db.get_preference("SOURCE_REDDIT_ENABLED", "true")).lower() == "true"
        use_rss = (await db.get_preference("SOURCE_RSS_ENABLED", "true")).lower() == "true"
        
        tasks = []
        if use_hn: tasks.append(self.hn_adapter.fetch_items())
        if use_rss: tasks.append(self.rss_adapter.fetch_items())
        if use_reddit: tasks.append(self.reddit_adapter.fetch_items())
        
        if not tasks:
            logger.warning("No sources enabled! Skipping ingestion.")
            return

        items = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                items.extend(res)
            else:
                logger.error(f"Adapter failed: {res}")

        logger.info(f"Ingested {len(items)} raw items.")
        
        # 2. Filter & Save
        print("Running Deduplication & Keyword Pre-filter...")
        count_saved = 0
        count_duplicates = 0
        count_irrelevant = 0
        
        # Deduplication Set (Simple In-Memory for this run)
        # In prod, this should check DB, but we do that via vector_store.has_id locally
        seen_hashes = set()

        for item in items:
            # 2.1 Fast URL/Title Combined Dedup
            # Normalize title for dedup (lowercase, remove non-alphanumeric)
            norm_title = "".join(x for x in item.title.lower() if x.isalnum())
            item_hash = f"{item.url}-{norm_title}"
            
            if item_hash in seen_hashes:
                count_duplicates += 1
                continue
            seen_hashes.add(item_hash)

            if vector_store.has_id(item.url):
                count_duplicates += 1
                continue
            
            # 2.2 Keyword Pre-filter (Fast)
            is_rel = await prefilter.is_relevant(item)
            if not is_rel:
                count_irrelevant += 1
                continue
            
            # 2.4 Save to DB 
            saved = await db.save_item(item)
            if saved:
                count_saved += 1

        vector_store.save_index()
        logger.info(f"Ingestion Complete. Saved {count_saved} new items. (Dropped {count_duplicates} dups, {count_irrelevant} irrelevant).")

    async def run_generation(self, summary_mode: bool = False):
        logger.info("Phase 2: Generation Started")
        
        # 1. Retrieve Candidates with Source Diversity
        # Fetch larger pool to ensure we can balance sources in Python
        recent_rows = await db.get_recent_items(limit=1000)
        
        # Determine allowed sources
        use_hn = (await db.get_preference("SOURCE_HN_ENABLED", "true")).lower() == "true"
        use_reddit = (await db.get_preference("SOURCE_REDDIT_ENABLED", "true")).lower() == "true"
        use_rss = (await db.get_preference("SOURCE_RSS_ENABLED", "true")).lower() == "true"
        
        logger.info(f"DEBUG: Source Prefs - HN:{use_hn}, Reddit:{use_reddit}, RSS:{use_rss}")

        candidates_by_source = {}
        processed_count = 0
        rss_count = 0
        
        for row in recent_rows:
            processed_count += 1
            # Reconstruct item
            item = IngestedItem(
                id=row['id'],
                source=row['source'],
                title=row['title'],
                url=row['url'],
                content=row['content'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                created_at=datetime.strptime(row['created_at'], "%Y-%m-%d %H:%M:%S") if isinstance(row['created_at'], str) else row['created_at'],
                raw_score=json.loads(row['metadata']).get('score', 0) if row['metadata'] else 0
            )
            
            # Group by source prefix (HN, Reddit, etc) and Filter
            src_key = item.source.split(":")[0].strip() # e.g. "HackerNews" from "HackerNews: Top"
            
            if src_key == "RSS": rss_count += 1
            
            # Apply Filtering
            if src_key == "HackerNews" and not use_hn: continue
            if src_key == "Reddit" and not use_reddit: continue
            if src_key == "RSS" and not use_rss: continue
            
            if src_key not in candidates_by_source:
                candidates_by_source[src_key] = []
            candidates_by_source[src_key].append(item)
            
        logger.info(f"DEBUG: Scanned {processed_count} items. Found {rss_count} RSS items before filter.")

        # Mix sources: Take top 50 from each source type (increased for more variety)
        mixed_candidates = []
        for src, items in candidates_by_source.items():
            # Sort by raw score (upvotes) if available, else newness
            items.sort(key=lambda x: x.raw_score if x.raw_score else 0, reverse=True)
            selected = items[:50]  # Increased from 30 to 50
            logger.info(f"Selected {len(selected)} items from {src}")
            mixed_candidates.extend(selected)
            
        # Global Deduplication on Title for candidates
        unique_candidates = []
        seen_titles = set()
        for item in mixed_candidates:
            norm_title = "".join(x for x in item.title.lower() if x.isalnum())
            if norm_title not in seen_titles:
                unique_candidates.append(item)
                seen_titles.add(norm_title)
        
        candidates = unique_candidates
        logger.info(f"Processing {len(candidates)} unique candidates for Digest generation...")

        # 2. Evaluate (Batch Mode)
        accepted_genai = []
        accepted_prod = []
        accepted_finance = []
        
        # Determine active personas dynamically from DB
        # Default to True if not found, or use settings as fallback
        is_genai = (await db.get_preference("PERSONA_GENAI_NEWS_ENABLED", "true")).lower() == "true"
        is_prod = (await db.get_preference("PERSONA_PRODUCT_IDEAS_ENABLED", "true")).lower() == "true"
        is_finance = (await db.get_preference("PERSONA_FINANCE_ENABLED", "true")).lower() == "true"

        active_personas = []
        if is_genai: active_personas.append("GENAI_NEWS")
        if is_prod: active_personas.append("PRODUCT_IDEAS")
        if is_finance: active_personas.append("FINANCIAL_ANALYSIS")
        
        # Log active personas
        logger.info(f"Active Personas (DB) - GenAI: {is_genai}, Product: {is_prod}, Finance: {is_finance}")

        BATCH_SIZE = 12 # Increased for efficiency
        MAX_CONCURRENT = 4 # Limit concurrent LLM calls to avoid overload
        
        # Progress tracking
        completed_tasks = 0
        total_tasks = 0
        
        # Build all evaluation tasks upfront for parallel processing
        async def evaluate_batch_task(persona_name: str, batch: list, batch_idx: int, task_num: int, total: int):
            """Wrapper to evaluate a batch and return results with metadata"""
            nonlocal completed_tasks
            try:
                logger.info(f"[Batch {batch_idx}] Evaluating {len(batch)} items for [{persona_name}]...")
                evaluator = EvaluatorFactory.get_evaluator(persona_name)
                results = await evaluator.evaluate_batch(batch)
                
                # Update progress
                completed_tasks += 1
                progress = (completed_tasks / total) * 100
                logger.info(f"✅ [Progress: {progress:.0f}%] Batch {batch_idx} [{persona_name}] complete ({completed_tasks}/{total})")
                
                return {"persona": persona_name, "batch": batch, "results": results, "error": None}
            except Exception as e:
                completed_tasks += 1
                progress = (completed_tasks / total) * 100
                logger.error(f"❌ [Progress: {progress:.0f}%] Batch {batch_idx} [{persona_name}] FAILED: {e}")
                return {"persona": persona_name, "batch": batch, "results": [], "error": str(e)}
        
        # Create all tasks
        batches = [candidates[i : i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
        total_tasks = len(batches) * len(active_personas)
        
        all_tasks = []
        task_num = 0
        for batch_idx, batch in enumerate(batches):
            for persona_name in active_personas:
                all_tasks.append(evaluate_batch_task(persona_name, batch, batch_idx, task_num, total_tasks))
                task_num += 1
        
        logger.info(f"🚀 Starting {total_tasks} evaluation tasks (max {MAX_CONCURRENT} concurrent)...")
        logger.info(f"📊 [Progress: 0%] Processing {len(candidates)} items in {len(batches)} batches...")
        
        # Process with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        # Execute all tasks in parallel with concurrency limit
        all_results = await asyncio.gather(*[limited_task(t) for t in all_tasks], return_exceptions=True)
        
        logger.info(f"🎉 [Progress: 100%] All {total_tasks} tasks completed!")
        
        # Process results - SMART EXCLUSIVE ASSIGNMENT
        # Each item goes to the persona where it scored HIGHEST
        
        # Collect all results per item across all personas
        item_scores = {}  # item_id -> {persona: (item, score, res)}
        
        for task_result in all_results:
            if isinstance(task_result, Exception):
                logger.error(f"Task failed with exception: {task_result}")
                continue
            if task_result.get("error"):
                continue
                
            persona_name = task_result["persona"]
            batch = task_result["batch"]
            results = task_result["results"]
            
            for res in results:
                item = next((x for x in batch if str(x.id) == res.item_id), None)
                if item and res.decision == "KEEP" and res.score >= 5:  # Changed > to >=
                    item_id = str(item.id)
                    
                    if item_id not in item_scores:
                        item_scores[item_id] = {}
                    
                    # Store score for this persona
                    item_scores[item_id][persona_name] = (item, res.score, res)
        
        # Assign each item to its BEST matching persona
        for item_id, persona_scores in item_scores.items():
            # Find which persona this item scored highest for
            best_persona = max(persona_scores.keys(), key=lambda p: persona_scores[p][1])
            item, score, res = persona_scores[best_persona]
            
            info_tuple = (item, res)
            if best_persona == "GENAI_NEWS": 
                accepted_genai.append(info_tuple)
            elif best_persona == "PRODUCT_IDEAS": 
                accepted_prod.append(info_tuple)
            elif best_persona == "FINANCIAL_ANALYSIS": 
                accepted_finance.append(info_tuple)
                
            logger.info(f"✅ KEEP [{best_persona}] {item.title[:50]}... (Score: {score})")

        # 3. Summarize & Format
        # Sort by score and limit to Top 5 per category
        accepted_genai.sort(key=lambda x: x[1].score, reverse=True)
        accepted_genai = accepted_genai[:5]
        
        accepted_prod.sort(key=lambda x: x[1].score, reverse=True)
        accepted_prod = accepted_prod[:5]
        
        accepted_finance.sort(key=lambda x: x[1].score, reverse=True)
        accepted_finance = accepted_finance[:5]

        summary_text = ""
        
        all_accepted = accepted_genai + accepted_prod + accepted_finance
        logger.info(f"Final Count: GenAI={len(accepted_genai)}, Product={len(accepted_prod)}, Finance={len(accepted_finance)}")
        
        if all_accepted:
            logger.info("Generating summary for accepted items...")
            try:
                summary_prompt = "Summarize the following findings into a cohesive executive summary:\n" + "\n".join([f"- {i[0].title}: {i[1].reasoning}" for i in all_accepted])
                summary_text = await llm.generate_text(summary_prompt)
            except Exception as e:
                logger.error(f"LLM Summary Generation Failed: {e}")
                summary_text = "Error generating summary: LLM request failed."
        else:
            logger.warning("No items were accepted by the evaluators. Digest will be empty.")
            summary_text = "No relevant items were found in this run matching your criteria."

        digest_md = self.format_digest(accepted_genai, accepted_prod, accepted_finance, summary_text)
        
        # 4. Deliver
        output_path = settings.DATA_DIR / f"digest_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(digest_md)
        logger.info(f"Digest written to {output_path}")

        # Check Delivery Preferences
        send_email_pref = (await db.get_preference("DELIVERY_EMAIL_ENABLED", "true")).lower() == "true"
        send_telegram_pref = (await db.get_preference("DELIVERY_TELEGRAM_ENABLED", "true")).lower() == "true"

        if settings.EMAIL_ENABLED and send_email_pref:
            from src.services.delivery import send_email
            await send_email("Daily AI Intelligence Digest", digest_md)

        if settings.TELEGRAM_ENABLED and send_telegram_pref:
            from src.services.delivery import send_telegram
            await send_telegram(digest_md)

    def format_digest(self, 
                      genai: List[Tuple[IngestedItem, EvaluationResult]], 
                      prod: List[Tuple[IngestedItem, EvaluationResult]],
                      finance: List[Tuple[IngestedItem, EvaluationResult]],
                      summary: str = "") -> str:
        
        lines = [f"# Total Recall: AI Intelligence Digest - {datetime.now().strftime('%Y-%m-%d')}\n"]
        
        if summary:
            lines.append("## 📝 Executive Summary\n")
            # Convert summary to blockquote for better visibility in email
            blockquote_summary = "\n".join([f"> {line}" for line in summary.splitlines()])
            lines.append(blockquote_summary)
            lines.append("\n---\n")

        if genai:
            lines.append("## 🤖 GenAI Tech News\n")
            genai.sort(key=lambda x: x[1].score, reverse=True)
            for item, res in genai:
                lines.append(f"### [{item.title}]({item.url})")
                lines.append(f"**Source:** {item.source}")
                lines.append(f"**Insight:** {res.reasoning}")
                if res.details.get('technical_details'):
                     lines.append(f"**Technical Details:** {res.details.get('technical_details')}")
                lines.append("")

        if prod:
            lines.append("\n## 💡 Product Opportunities\n")
            prod.sort(key=lambda x: x[1].score, reverse=True)
            for item, res in prod:
                lines.append(f"### [{item.title}]({item.url})")
                lines.append(f"**Source:** {item.source}")
                lines.append(f"**Insight:** {res.reasoning}")
                lines.append("")
        
        if finance:
            lines.append("\n## 💰 Financial Analysis\n")
            finance.sort(key=lambda x: x[1].score, reverse=True)
            for item, res in finance:
                lines.append(f"### [{item.title}]({item.url})")
                lines.append(f"**Source:** {item.source}")
                lines.append(f"**Insight:** {res.reasoning}")
                if res.details.get('key_metrics'):
                    lines.append(f"**Metrics:** {res.details.get('key_metrics')}")
                lines.append("")
                
        return "\n".join(lines)

pipeline = Pipeline()
