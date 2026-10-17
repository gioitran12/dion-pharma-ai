"""
DION Healthcare AI — OpenAI LLM Provider
Triển khai BaseLLMProvider sử dụng OpenAI AsyncOpenAI client chính thức.
"""

import os
import time
from typing import Optional, Dict

from openai import (
    AsyncOpenAI,
    APIError,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
)

from modules.chat.providers.base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResult,
    LLMConfigurationError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMEmptyResponseError,
    LLMProviderError,
)


class OpenAIProvider(BaseLLMProvider):
    """Provider cho OpenAI sử dụng SDK openai phiên bản mới."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        client: Optional[AsyncOpenAI] = None,
    ):
        provider_name = "openai"
        resolved_model = model_name or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        super().__init__(provider_name=provider_name, model_name=resolved_model)

        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._injected_client = client
        self._client: Optional[AsyncOpenAI] = client

    def validate_configuration(self) -> None:
        """Kiểm tra tính hợp lệ của OpenAI API Key."""
        if self._injected_client is not None:
            return

        if not self._api_key or not self._api_key.strip():
            raise LLMConfigurationError(
                "OPENAI_API_KEY chưa được cấu hình. Vui lòng thiết lập biến môi trường OPENAI_API_KEY.",
                code="LLM_NOT_CONFIGURED"
            )

        lowered = self._api_key.strip().lower()
        if "your_" in lowered or "placeholder" in lowered or "example" in lowered:
            raise LLMConfigurationError(
                "OPENAI_API_KEY đang chứa giá trị mẫu (placeholder). Vui lòng cung cấp API key thật.",
                code="LLM_NOT_CONFIGURED"
            )

    def _get_client(self) -> AsyncOpenAI:
        """Khởi tạo AsyncOpenAI client nếu chưa có."""
        if self._client is not None:
            return self._client
        self.validate_configuration()
        self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResult:
        """Gửi prompt tới OpenAI Chat Completions API và trả về LLMResult."""
        client = self._get_client()

        # Xây dựng messages
        api_messages = []
        if request.system_instruction:
            api_messages.append({"role": "system", "content": request.system_instruction})

        if request.messages and len(request.messages) > 0:
            for m in request.messages:
                api_messages.append({"role": m.role, "content": m.content})
        else:
            prompt_text = request.get_full_prompt_text()
            if not prompt_text:
                raise LLMEmptyResponseError("Request prompt is empty.")
            api_messages.append({"role": "user", "content": prompt_text})

        timeout = request.timeout_seconds if request.timeout_seconds else 20.0
        start_time = time.perf_counter()

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                stop=request.stop_sequences,
                timeout=timeout,
            )
        except AuthenticationError as e:
            raise LLMAuthenticationError("OpenAI API key không hợp lệ hoặc không có quyền truy cập.")
        except RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {e.message}")
        except APITimeoutError as e:
            raise LLMTimeoutError(f"OpenAI request timed out after {timeout}s.")
        except APIConnectionError as e:
            raise LLMProviderError(f"OpenAI connection error: {e.message}", code="LLM_NETWORK_ERROR", retryable=True)
        except APIError as e:
            status_code = getattr(e, "status_code", 500)
            err_msg = str(e.message)
            if self._api_key and self._api_key in err_msg:
                err_msg = err_msg.replace(self._api_key, "[REDACTED_API_KEY]")
            if status_code == 404:
                raise LLMProviderError(err_msg, code="LLM_MODEL_NOT_FOUND", retryable=False, status_code=404)
            retryable = status_code >= 500
            raise LLMProviderError(err_msg, code="LLM_PROVIDER_ERROR", retryable=retryable, status_code=status_code)
        except Exception as e:
            if isinstance(e, (LLMConfigurationError, LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError, LLMEmptyResponseError, LLMProviderError)):
                raise e
            err_str = str(e)
            if self._api_key and self._api_key in err_str:
                err_str = err_str.replace(self._api_key, "[REDACTED_API_KEY]")
            if "timeout" in err_str.lower():
                raise LLMTimeoutError(f"OpenAI request timed out: {err_str}")
            raise LLMProviderError(f"Unexpected OpenAI error: {err_str}", retryable=False)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not response.choices or not response.choices[0].message:
            raise LLMEmptyResponseError("OpenAI returned no choices.")

        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        if not content:
            raise LLMEmptyResponseError("OpenAI returned empty message content.")

        usage_dict: Optional[Dict[str, int]] = None
        if response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResult(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            usage=usage_dict,
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason,
            request_id=response.id,
        )
