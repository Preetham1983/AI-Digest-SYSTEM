import asyncio
import ollama
from src.config import settings
from src.services.logger import logger
import json
from typing import Dict, Any

class LLMService:
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model = settings.OLLAMA_MODEL

    async def generate_json(self, prompt: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generates JSON output from the LLM.
        """
        try:
            # Force JSON mode
            response = await self.client.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ], format='json', options={'temperature': 0.1})
            
            content = response['message']['content']
            
            # Parse JSON
            try:
                data = json.loads(content)
                return data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from LLM: {content}")
                return {}
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            return {}

    async def generate_text(self, prompt: str) -> str:
        try:
            response = await self.client.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ], options={'temperature': 0.3})
            return response['message']['content']
        except Exception as e:
            logger.error(f"LLM Text Gen failed: {e}")
            return ""

llm = LLMService()
