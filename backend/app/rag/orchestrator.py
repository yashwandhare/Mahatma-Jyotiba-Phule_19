"""Orchestrator for LLM provider selection and execution with retries."""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

import urllib.error
import urllib.request
import json
from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from backend.app.core import config

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM request."""
    model: str
    temperature: float = 0.1
    max_tokens: int = 500
    timeout: int = 45
    max_retries: int = 2


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class ProviderUnavailable(LLMProviderError):
    """Provider is offline or unconfigured."""
    pass


class ProviderTimeout(LLMProviderError):
    """Provider request timed out."""
    pass


class _GroqProvider:
    """Groq API client with retry logic."""
    
    def __init__(self):
        self._client: Optional[OpenAI] = None
    
    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not config.GROQ_API_KEY:
                raise ProviderUnavailable("GROQ_API_KEY not configured.")
            
            self._client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=config.GROQ_API_KEY,
                timeout=config.LLM_TIMEOUT,
            )
        return self._client
    
    def generate(self, system_prompt: str, user_message: str, llm_config: LLMConfig) -> str:
        """Generate completion with retry logic."""
        if config.OFFLINE_MODE:
            raise ProviderUnavailable("Offline mode enabled; Groq is disabled.")
        
        client = self._get_client()
        last_error = None
        
        for attempt in range(llm_config.max_retries + 1):
            try:
                logger.info(f"Groq request (attempt {attempt + 1}/{llm_config.max_retries + 1})")
                
                response = client.chat.completions.create(
                    model=llm_config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens
                )
                return response.choices[0].message.content.strip()
                
            except APITimeoutError as e:
                last_error = e
                logger.warning(f"Groq timeout on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except RateLimitError as e:
                last_error = e
                logger.warning(f"Groq rate limit on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(5)
                    
            except APIError as e:
                last_error = e
                logger.error(f"Groq API error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(1)
                else:
                    break
        
        raise ProviderTimeout(f"Groq failed after {llm_config.max_retries + 1} attempts: {last_error}")


class _OllamaProvider:
    """Ollama local API client with retry logic."""
    
    def generate(self, system_prompt: str, user_message: str, llm_config: LLMConfig) -> str:
        """Generate completion with retry logic."""
        url = f"{config.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": llm_config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False
        }
        
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        last_error = None
        for attempt in range(llm_config.max_retries + 1):
            try:
                logger.info(f"Ollama request (attempt {attempt + 1}/{llm_config.max_retries + 1})")
                
                with urllib.request.urlopen(request, timeout=llm_config.timeout) as response:
                    body = response.read().decode("utf-8")
                
                parsed = json.loads(body)
                message = parsed.get("message", {})
                content = message.get("content") or parsed.get("response", "")
                
                if not content:
                    raise RuntimeError("Ollama returned empty response.")
                
                return content.strip()
                
            except urllib.error.URLError as e:
                last_error = e
                logger.warning(f"Ollama connection error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                    
            except Exception as e:
                last_error = e
                logger.error(f"Ollama error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(1)
                else:
                    break
        
        raise ProviderUnavailable(f"Ollama unreachable at {config.OLLAMA_BASE_URL} after {llm_config.max_retries + 1} attempts: {last_error}")


class LLMOrchestrator:
    """Single orchestration point for all LLM interactions."""
    
    def __init__(self):
        self._groq = _GroqProvider()
        self._ollama = _OllamaProvider()
    
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate LLM completion using configured provider.
        
        Args:
            system_prompt: System instruction
            user_message: User query with context
            provider: Override default provider (groq/ollama)
            model: Override default model
            temperature: Override temperature
            max_tokens: Override max tokens
            
        Returns:
            Generated text response
            
        Raises:
            ProviderUnavailable: Provider is offline or misconfigured
            ProviderTimeout: Request timed out with retries
        """
        # Use overrides or defaults
        provider = (provider or config.RAG_PROVIDER).lower()
        model = model or config.RAG_MODEL_NAME
        
        llm_config = LLMConfig(
            model=model,
            temperature=temperature or config.GENERATION_TEMPERATURE,
            max_tokens=max_tokens or config.GENERATION_MAX_TOKENS,
            timeout=config.LLM_TIMEOUT,
            max_retries=2,
        )
        
        logger.info(f"Orchestrating LLM: provider={provider}, model={model}")
        
        if provider == "groq":
            return self._groq.generate(system_prompt, user_message, llm_config)
        elif provider == "ollama":
            return self._ollama.generate(system_prompt, user_message, llm_config)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def check_availability(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if provider is available.
        
        Returns:
            Dict with status, provider, and message
        """
        provider = (provider or config.RAG_PROVIDER).lower()
        
        if provider == "groq":
            if config.OFFLINE_MODE:
                return {"available": False, "provider": "groq", "reason": "offline_mode"}
            if not config.GROQ_API_KEY:
                return {"available": False, "provider": "groq", "reason": "no_api_key"}
            return {"available": True, "provider": "groq"}
            
        elif provider == "ollama":
            # Try quick ping to Ollama
            try:
                url = f"{config.OLLAMA_BASE_URL}/api/tags"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        return {"available": True, "provider": "ollama"}
            except Exception as e:
                return {"available": False, "provider": "ollama", "reason": str(e)}
        
        return {"available": False, "provider": provider, "reason": "unknown_provider"}


# Global singleton
_orchestrator: Optional[LLMOrchestrator] = None


def get_orchestrator() -> LLMOrchestrator:
    """Get global LLM orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator()
    return _orchestrator
