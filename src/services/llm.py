import asyncio
import ollama
from src.config import settings
from src.services.logger import logger
import json
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class LLMService:
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model = settings.OLLAMA_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda retry_state: logger.warning(
            f"LLM call failed, retrying in {retry_state.next_action.sleep} seconds... (attempt {retry_state.attempt_number})"
        )
    )
    async def generate_json(self, prompt: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generates JSON output from the LLM with retry on failure.
        """
        try:
            response = await self.client.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ], format='json', options={'temperature': 0.1})
            
            content = response['message']['content']
            
            try:
                data = json.loads(content)
                return data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from LLM: {content}")
                return {}
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            raise  # Re-raise to trigger retry

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda retry_state: logger.warning(
            f"LLM call failed, retrying in {retry_state.next_action.sleep} seconds... (attempt {retry_state.attempt_number})"
        )
    )
    async def generate_text(self, prompt: str) -> str:
        """
        Generates text output from the LLM with retry on failure.
        """
        try:
            response = await self.client.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ], options={'temperature': 0.3})
            return response['message']['content']
        except Exception as e:
            logger.error(f"LLM Text Gen failed: {e}")
            raise  # Re-raise to trigger retry

llm = LLMService()

