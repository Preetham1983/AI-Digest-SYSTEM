from abc import ABC, abstractmethod
from typing import Dict, Any, List
import numpy as np
from src.models.items import IngestedItem, EvaluationResult
from src.services.llm import llm
from src.services.logger import logger
from src.services.embedding import get_model, get_embeddings_batch
from src.config import settings

# Persona anchor texts for semantic scoring
PERSONA_ANCHORS = {
    "GENAI_NEWS": """
        Large Language Models, LLM, GPT, Claude, Llama, Gemini, AI, machine learning,
        deep learning, neural networks, transformers, AI agents, RAG, embeddings,
        fine-tuning, training, inference, CUDA, GPU, PyTorch, TensorFlow,
        AI research, model releases, open source AI, prompt engineering.
    """,
    "PRODUCT_IDEAS": """
        Startup, product launch, SaaS, app, software, developer tools,
        market opportunity, business idea, MVP, growth, entrepreneurship,
        indie hacker, bootstrapping, API, platform, marketplace.
    """,
    "FINANCIAL_ANALYSIS": """
        Revenue, earnings, funding, Series A, venture capital, IPO,
        stock, valuation, investment, financial report, quarterly results,
        market cap, acquisition, merger, tech stocks.
    """
}

class BaseEvaluator(ABC):
    def __init__(self):
        self._anchor_embedding = None
    
    @abstractmethod
    def get_persona_name(self) -> str:
        pass

    def _get_anchor_embedding(self):
        """Get cached anchor embedding for this persona using shared model"""
        if self._anchor_embedding is None:
            model = get_model()  # Use shared singleton
            anchor_text = PERSONA_ANCHORS.get(self.get_persona_name(), "")
            self._anchor_embedding = model.encode(anchor_text, normalize_embeddings=True)
        return self._anchor_embedding

    def _compute_semantic_scores(self, items: List[IngestedItem]) -> List[float]:
        """Batch compute semantic similarity scores using shared model"""
        anchor_emb = self._get_anchor_embedding()
        
        # Batch encode all items using shared model
        texts = [(item.title + " " + (item.content or ""))[:512] for item in items]
        item_embeddings = get_embeddings_batch(texts, normalize=True, show_progress=False)
        
        # Compute cosine similarity (dot product of normalized vectors)
        scores = np.dot(item_embeddings, anchor_emb)
        return scores.tolist()

    @abstractmethod
    def get_prompt_template(self) -> str:
        pass

    async def evaluate_batch(self, items: List[IngestedItem]) -> List[EvaluationResult]:
        persona = self.get_persona_name()
        if not items:
            return []
        
        # Step 1: Quick semantic pre-filter (VERY lenient - only removes obvious junk)
        logger.info(f"[{persona}] Running semantic pre-filter...")
        semantic_scores = self._compute_semantic_scores(items)
        
        items_for_llm = []
        results = []
        
        for item, score in zip(items, semantic_scores):
            if score >= settings.SEMANTIC_THRESHOLD:
                items_for_llm.append(item)
            else:
                # Only discard if VERY low score
                logger.debug(f"  ❌ Filtered (score={score:.3f}): {item.title[:50]}...")
                results.append(EvaluationResult(
                    item_id=str(item.id),
                    persona=persona,
                    score=0,
                    decision="DISCARD",
                    reasoning=f"Low relevance (cosine={score:.2f})",
                    details={"semantic_score": score}
                ))
        
        filtered_count = len(items) - len(items_for_llm)
        logger.info(f"[{persona}] Semantic filter: {len(items_for_llm)}/{len(items)} items passed (filtered {filtered_count} obvious junk)")
        
        # Step 2: LLM evaluation for remaining items
        if not items_for_llm:
            return results
            
        # Format batch prompt
        items_str = "\n\n".join([item.to_prompt_string() for item in items_for_llm])
        prompt = self.get_batch_prompt_template().format(items_content=items_str)
        
        # Call LLM
        response_text = await llm.generate_text(prompt)
        
        # Parse Batch Response
        lines = response_text.strip().split('\n')
        item_map = {str(item.id): item for item in items_for_llm}
        parsed_ids = set()
        
        for line in lines:
            line = line.strip()
            if not line or "ID:" not in line:
                continue
                
            try:
                parts = [p.strip() for p in line.split('|')]
                id_part = next((p for p in parts if p.startswith("ID:")), None)
                if not id_part:
                    continue
                    
                item_id = id_part.replace("ID:", "").strip()
                original_item = item_map.get(item_id)
                
                if original_item:
                    result = self.parse_line(original_item, line)
                    if result:
                        results.append(result)
                        parsed_ids.add(item_id)
            except Exception as e:
                logger.error(f"Failed to parse batch line: {line} - {e}")
                continue
        
        # Fallback for items not parsed (LLM missed them)
        for item_id, item in item_map.items():
            if item_id not in parsed_ids:
                results.append(EvaluationResult(
                    item_id=item_id,
                    persona=persona,
                    score=5,
                    decision="KEEP",
                    reasoning="Passed semantic filter, pending review",
                    details={}
                ))
                
        return results

    @abstractmethod
    def get_batch_prompt_template(self) -> str:
        pass
        
    @abstractmethod
    def parse_line(self, item: IngestedItem, line: str) -> EvaluationResult:
        pass

    async def evaluate(self, item: IngestedItem) -> EvaluationResult:
        return (await self.evaluate_batch([item]))[0]
    
    @abstractmethod
    def parse_response(self, item: IngestedItem, text: str) -> EvaluationResult:
        pass


class GenAiEvaluator(BaseEvaluator):
    def get_persona_name(self) -> str:
        return "GENAI_NEWS"

    def get_batch_prompt_template(self) -> str:
        return """
You are an expert AI Editor.
Analyze the following list of content items.

GUIDELINES:
- Select items relevant to a Generative AI Engineer.
- STRICTLY DISCARD generic non-technical news.
- IGNORE duplicates.

INPUT ITEMS:
{items_content}

OUTPUT FORMAT:
For EACH item, output a SINGLE LINE in this exact format:
ID: <UUID> | SCORE: <0-10> | DECISION: <KEEP/DISCARD> | INSIGHT: <4 sentences explaining the core value and key takeaways. Be specific and clear to help a user decide if they should read the full article.>

Output ONLY these lines.
"""

    def parse_line(self, item: IngestedItem, line: str) -> EvaluationResult:
        data = {}
        parts = [p.strip() for p in line.split('|')]
        for part in parts:
            if ':' in part:
                k, v = part.split(':', 1)
                data[k.strip().upper()] = v.strip()
        
        score = float(data.get('SCORE', 0))
        decision = data.get('DECISION', 'DISCARD').upper()
        if 'KEEP' in decision and score >= 5: 
            decision = 'KEEP'
        else: 
            decision = 'DISCARD'
            
        return EvaluationResult(
            item_id=str(item.id),
            persona=self.get_persona_name(),
            score=score,
            decision=decision,
            reasoning=data.get('INSIGHT', ''),
            details={'raw_line': line}
        )
        
    def get_prompt_template(self) -> str: 
        return ""
    
    def parse_response(self, item, text): 
        return None


class ProductEvaluator(BaseEvaluator):
    def get_persona_name(self) -> str:
        return "PRODUCT_IDEAS"

    def get_batch_prompt_template(self) -> str:
        return """
You are a Product Scout. Analyze the items.
Look for: Startup ideas, unaddressed problems, or market gaps.

INPUT ITEMS:
{items_content}

OUTPUT FORMAT:
For EACH item, output a SINGLE LINE in this exact format:
ID: <UUID> | SCORE: <0-10> | DECISION: <KEEP/DISCARD> | INSIGHT: <4 sentences describing the core problem or opportunity. Be specific and clear to help a user decide if they should read the full article.>

Output ONLY these lines.
"""

    def parse_line(self, item: IngestedItem, line: str) -> EvaluationResult:
        data = {}
        parts = [p.strip() for p in line.split('|')]
        for part in parts:
            if ':' in part:
                k, v = part.split(':', 1)
                data[k.strip().upper()] = v.strip()
        
        score = float(data.get('SCORE', 0))
        decision = data.get('DECISION', 'DISCARD').upper()
        if 'KEEP' in decision and score >= 5: 
            decision = 'KEEP'
        else: 
            decision = 'DISCARD'

        return EvaluationResult(
            item_id=str(item.id),
            persona=self.get_persona_name(),
            score=score,
            decision=decision,
            reasoning=data.get('INSIGHT', ''),
            details={'raw_line': line}
        )
    
    def get_prompt_template(self) -> str: 
        return ""
    
    def parse_response(self, item, text): 
        return None


class FinanceEvaluator(BaseEvaluator):
    def get_persona_name(self) -> str:
        return "FINANCIAL_ANALYSIS"

    def get_batch_prompt_template(self) -> str:
        return """
You are a Financial Analyst. Analyze the items.
Look for: Revenue, Funding, IPOs, Market Data.

INPUT ITEMS:
{items_content}

OUTPUT FORMAT:
For EACH item, output a SINGLE LINE in this exact format:
ID: <UUID> | SCORE: <0-10> | DECISION: <KEEP/DISCARD> | INSIGHT: <4 sentences summarizing the key financial numbers and status. Be specific and clear to help a user decide if they should read the full article.>

Output ONLY these lines.
"""

    def parse_line(self, item: IngestedItem, line: str) -> EvaluationResult:
        data = {}
        parts = [p.strip() for p in line.split('|')]
        for part in parts:
            if ':' in part:
                k, v = part.split(':', 1)
                data[k.strip().upper()] = v.strip()
        
        score = float(data.get('SCORE', 0))
        decision = data.get('DECISION', 'DISCARD').upper()
        if 'KEEP' in decision and score >= 5: 
            decision = 'KEEP'
        else: 
            decision = 'DISCARD'

        return EvaluationResult(
            item_id=str(item.id),
            persona=self.get_persona_name(),
            score=score,
            decision=decision,
            reasoning=data.get('INSIGHT', ''),
            details={'raw_line': line}
        )
    
    def get_prompt_template(self) -> str: 
        return ""
    
    def parse_response(self, item, text): 
        return None


class EvaluatorFactory:
    @staticmethod
    def get_evaluator(persona: str) -> BaseEvaluator:
        if persona == "GENAI_NEWS":
            return GenAiEvaluator()
        elif persona == "PRODUCT_IDEAS":
            return ProductEvaluator()
        elif persona == "FINANCIAL_ANALYSIS":
            return FinanceEvaluator()
        else:
            raise ValueError(f"Unknown persona: {persona}")
