"""Orchestrator for LLM provider selection and execution with retries."""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

import urllib.error
import urllib.request
import urllib.parse
import json
from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from backend.app.core import config
from backend.app.core.errors import get_error_message

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
    """Groq API client with standardized retry logic and error handling."""
    
    def __init__(self):
        self._client: Optional[OpenAI] = None
    
    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not config.GROQ_API_KEY:
                raise ProviderUnavailable(get_error_message("provider_unavailable"))
            
            self._client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=config.GROQ_API_KEY,
                timeout=config.LLM_TIMEOUT,
            )
        return self._client
    
    def generate(self, system_prompt: str, user_message: str, llm_config: LLMConfig) -> str:
        """
        Generate completion with standardized retry logic.
        
        Provider Interface Contract:
        - Retries: 2 attempts with exponential backoff
        - Timeout errors → ProviderTimeout
        - Connection/availability errors → ProviderUnavailable
        - Empty responses → ProviderUnavailable
        """
        if config.OFFLINE_MODE:
            raise ProviderUnavailable(get_error_message("offline_mode"))
        
        client = self._get_client()
        last_error = None
        is_timeout = False
        
        for attempt in range(llm_config.max_retries + 1):
            try:
                logger.info(f"LLM request (attempt {attempt + 1}/{llm_config.max_retries + 1})")
                
                response = client.chat.completions.create(
                    model=llm_config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens
                )
                
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise ProviderUnavailable("Provider returned empty response.")
                
                return content.strip()
                
            except APITimeoutError as e:
                last_error = e
                is_timeout = True
                logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                    
            except (RateLimitError, APIError) as e:
                last_error = e
                logger.warning(f"Provider error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    break
            
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    break
        
        # Normalize error types: timeouts always raise ProviderTimeout
        if is_timeout:
            raise ProviderTimeout(get_error_message("provider_timeout"))
        else:
            raise ProviderUnavailable(get_error_message("provider_unavailable"))


class _OllamaProvider:
    """Ollama local API client with standardized retry logic and error handling."""
    
    def generate(self, system_prompt: str, user_message: str, llm_config: LLMConfig) -> str:
        """
        Generate completion with standardized retry logic.
        
        Provider Interface Contract:
        - Retries: 2 attempts with exponential backoff
        - Timeout errors → ProviderTimeout
        - Connection/availability errors → ProviderUnavailable
        - Empty responses → ProviderUnavailable
        """
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
        is_timeout = False
        
        for attempt in range(llm_config.max_retries + 1):
            try:
                logger.info(f"LLM request (attempt {attempt + 1}/{llm_config.max_retries + 1})")
                
                with urllib.request.urlopen(request, timeout=llm_config.timeout) as response:
                    body = response.read().decode("utf-8")
                
                parsed = json.loads(body)
                message = parsed.get("message", {})
                content = message.get("content") or parsed.get("response", "")
                
                if not content or not content.strip():
                    raise ProviderUnavailable("Provider returned empty response.")
                
                return content.strip()
                
            except TimeoutError as e:
                last_error = e
                is_timeout = True
                logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                    
            except urllib.error.URLError as e:
                last_error = e
                # URLError with timeout reason is treated as timeout
                if hasattr(e, 'reason') and 'timed out' in str(e.reason).lower():
                    is_timeout = True
                logger.warning(f"Provider error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    break
                    
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < llm_config.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    break
        
        # Normalize error types: timeouts always raise ProviderTimeout
        if is_timeout:
            raise ProviderTimeout(get_error_message("provider_timeout"))
        else:
            raise ProviderUnavailable(get_error_message("provider_unavailable"))


class LLMOrchestrator:
    """
    Single orchestration point for all LLM interactions with strict provider interface.
    
    Provider Interface Contract (enforced for both Groq and Ollama):
    - Input: system_prompt, user_message, LLMConfig (model, temp, tokens, timeout)
    - Output: text string (stripped, non-empty)
    - Retry behavior: 2 retries with exponential backoff (2^attempt seconds)
    - Timeout handling: All timeout errors → ProviderTimeout exception
    - Availability errors: Connection/config/empty response → ProviderUnavailable
    - Error messages: Normalized via get_error_message(), no provider-specific text
    - Logging: Generic "LLM request" messages, no provider name in output
    
    This ensures providers are completely interchangeable - callers cannot detect
    which provider is active based on errors, timing, or response structure.
    """
    
    def __init__(self):
        self._groq = _GroqProvider()
        self._ollama = _OllamaProvider()

    def _ensure_offline_policy(self, provider: str) -> None:
        """
        Enforce offline-mode restrictions before any network call.
        
        INVARIANT: OFFLINE_MODE=1 forbids all remote network calls.
        See INVARIANTS.md §3 for details.
        """
        if not config.OFFLINE_MODE:
            return

        # GUARD: No non-Ollama providers in offline mode
        if provider != "ollama":
            raise ProviderUnavailable(get_error_message("offline_mode"))

        parsed = urllib.parse.urlparse(config.OLLAMA_BASE_URL)
        host = (parsed.hostname or "").lower()
        local_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
        if not host or (host not in local_hosts and not host.startswith("127.")):
            raise ProviderUnavailable(get_error_message("offline_local_ollama"))
    
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
            ValueError: Critical configuration is missing or invalid
        """
        # Validate runtime requirements before attempting generation
        try:
            config.settings.validate_runtime_requirements()
        except ValueError as e:
            raise ProviderUnavailable(str(e))
        
        # Use overrides or defaults
        provider = (provider or config.RAG_PROVIDER).lower()
        model = model or config.RAG_MODEL_NAME
        
        self._ensure_offline_policy(provider)

        llm_config = LLMConfig(
            model=model,
            temperature=temperature or config.GENERATION_TEMPERATURE,
            max_tokens=max_tokens or config.GENERATION_MAX_TOKENS,
            timeout=config.LLM_TIMEOUT,
            max_retries=2,
        )
        
        logger.info(f"Generating LLM response: model={model}")
        
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
