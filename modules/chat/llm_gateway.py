"""
DION Healthcare AI — LLM Gateway
Lớp cổng kết nối LLM trung tâm, chịu trách nhiệm:
1. Xác định và khởi tạo provider theo cấu hình (Gemini / OpenAI / Fake).
2. Kiểm tra cấu hình và API key.
3. Chuyển đổi dữ liệu sang định dạng API tương ứng.
4. Quản lý timeout và bounded retries cho các lỗi tạm thời (không retry lỗi xác thực).
5. Chuẩn hóa kết quả LLMResult và token usage.
6. Bảo vệ an toàn: tuyệt đối không fallback ngầm sang Mock khi gặp lỗi thực tế.
"""

import os
import time
import asyncio
import logging
import hashlib
from typing import Optional, List, Dict, Any, Tuple

from modules.chat.providers.base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResult,
    LLMMessage,
    LLMError,
    LLMConfigurationError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMEmptyResponseError,
    LLMProviderError,
)
from modules.chat.providers.gemini_provider import GeminiProvider
from modules.chat.providers.openai_provider import OpenAIProvider
from modules.chat.providers.fake_provider import FakeLLMProvider
from modules.chat.prompts.system_prompts import get_system_prompt

logger = logging.getLogger("dion.chat.gateway")


class LLMGateway:
    """Gateway kết nối các mô hình ngôn ngữ lớn (LLM) cho DION AI Copilot."""

    SUPPORTED_PROVIDERS = {"gemini", "openai", "fake"}
    _RESPONSE_CACHE: Dict[str, Any] = {}
    _CACHE_TTL_SECONDS: float = 1800.0  # 30 phút TTL
    _MAX_CACHE_ENTRIES: int = 500

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay_seconds: Optional[float] = None,
    ):
        # Số lần retry tối đa: kiểm soát giới hạn, đọc từ biến môi trường LLM_MAX_RETRIES nếu có
        env_retries = os.getenv("LLM_MAX_RETRIES")
        if max_retries is not None:
            self.max_retries = max(0, max_retries)
        elif env_retries and env_retries.strip():
            try:
                self.max_retries = max(0, min(5, int(env_retries.strip())))
            except ValueError:
                self.max_retries = 3
        else:
            self.max_retries = 3

        # Khoảng trễ ban đầu (seconds): đọc từ biến môi trường LLM_RETRY_DELAY_SECONDS nếu có
        env_delay = os.getenv("LLM_RETRY_DELAY_SECONDS")
        if retry_delay_seconds is not None:
            self.retry_delay_seconds = max(0.0, retry_delay_seconds)
        elif env_delay and env_delay.strip():
            try:
                self.retry_delay_seconds = max(0.0, min(10.0, float(env_delay.strip())))
            except ValueError:
                self.retry_delay_seconds = 1.0
        else:
            self.retry_delay_seconds = 1.0

        # Timeout cấu hình từ tham số hoặc biến môi trường
        env_timeout = os.getenv("LLM_TIMEOUT_SECONDS")
        if timeout_seconds is not None:
            self.timeout_seconds = float(timeout_seconds)
        elif env_timeout and env_timeout.strip():
            try:
                self.timeout_seconds = float(env_timeout.strip())
            except ValueError:
                self.timeout_seconds = 20.0
        else:
            self.timeout_seconds = 20.0

        # Max output tokens từ biến môi trường
        env_tokens = os.getenv("LLM_MAX_OUTPUT_TOKENS")
        if env_tokens and env_tokens.strip():
            try:
                self.max_output_tokens = int(env_tokens.strip())
            except ValueError:
                self.max_output_tokens = 512
        else:
            self.max_output_tokens = 512

        # Nếu truyền provider instance trực tiếp (Dependency Injection trong unit test)
        if provider is not None:
            self._provider = provider
            self.provider_name = provider.provider_name
            self.model_name = provider.model_name
        else:
            # Xác định provider từ tham số hoặc biến môi trường
            raw_p_name = provider_name or os.getenv("LLM_PROVIDER") or "gemini"
            p_name = raw_p_name.strip().lower()
            if p_name not in self.SUPPORTED_PROVIDERS:
                raise LLMConfigurationError(
                    f"Provider '{p_name}' không được hỗ trợ. Các provider hợp lệ: {sorted(list(self.SUPPORTED_PROVIDERS))}.",
                    code="LLM_INVALID_PROVIDER"
                )

            self.provider_name = p_name
            self.model_name = model_name or os.getenv("LLM_MODEL")
            self._provider = self._create_provider(p_name, self.model_name)

    def _create_provider(self, provider_name: str, model_name: Optional[str]) -> BaseLLMProvider:
        """Khởi tạo provider tương ứng."""
        if provider_name == "gemini":
            return GeminiProvider(model_name=model_name)
        elif provider_name == "openai":
            return OpenAIProvider(model_name=model_name)
        elif provider_name == "fake":
            return FakeLLMProvider(model_name=model_name or "fake-model")
        else:
            raise LLMConfigurationError(
                f"Không thể khởi tạo provider '{provider_name}'.",
                code="LLM_INVALID_PROVIDER"
            )

    def validate_configuration(self) -> None:
        """Kiểm tra cấu hình và thông tin xác thực của provider đang chọn."""
        self._provider.validate_configuration()

    async def generate(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResult:
        """
        Thực hiện gửi request tới LLM qua Provider đã cấu hình,
        áp dụng timeout, retry có kiểm soát và chuẩn hóa kết quả.
        """
        # Kiểm tra tính hợp lệ cấu hình trước khi gọi
        self.validate_configuration()

        # Áp dụng system instruction mặc định từ backend nếu không truyền
        sys_inst = system_instruction or get_system_prompt("copilot")

        req = LLMRequest(
            prompt=prompt,
            messages=messages,
            system_instruction=sys_inst,
            temperature=temperature,
            max_output_tokens=max_output_tokens or self.max_output_tokens,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
            stop_sequences=stop_sequences,
        )

        # 1. Kiểm tra cache câu trả lời tức thì (< 0.01s)
        cache_key = None
        prompt_text = req.get_full_prompt_text()
        if prompt_text and req.temperature <= 0.4:
            raw_key = f"{self.provider_name}:{self.model_name}:{round(req.temperature, 2)}:{req.system_instruction}:{prompt_text}"
            cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            now = time.time()
            if cache_key in self._RESPONSE_CACHE:
                cached_res, exp = self._RESPONSE_CACHE[cache_key]
                if now < exp:
                    logger.info(f"[LLMGateway] Cache HIT for key {cache_key[:12]} (Instant response)")
                    return cached_res

        attempts = 0
        last_error: Optional[Exception] = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                result = await self._provider.generate(req)
                if cache_key and result and result.content:
                    now = time.time()
                    if len(self._RESPONSE_CACHE) >= self._MAX_CACHE_ENTRIES:
                        oldest_k = next(iter(self._RESPONSE_CACHE))
                        self._RESPONSE_CACHE.pop(oldest_k, None)
                    self._RESPONSE_CACHE[cache_key] = (result, now + self._CACHE_TTL_SECONDS)
                return result
            except (LLMAuthenticationError, LLMConfigurationError) as non_retryable:
                # Tuyệt đối KHÔNG retry lỗi sai khóa hoặc lỗi cấu hình
                logger.error(f"[LLMGateway] Non-retryable error ({non_retryable.code}): {non_retryable.message}")
                raise non_retryable
            except LLMEmptyResponseError as empty_err:
                # Không retry lỗi rỗng trừ khi muốn thử lại
                logger.warning(f"[LLMGateway] Empty response received: {empty_err.message}")
                raise empty_err
            except LLMError as llm_err:
                last_error = llm_err
                if not llm_err.retryable or attempts > self.max_retries:
                    logger.error(f"[LLMGateway] Provider error ({llm_err.code}) after {attempts} attempts: {llm_err.message}")
                    raise llm_err

                delay = min(self.retry_delay_seconds * (2 ** (attempts - 1)), 8.0)
                logger.warning(f"[LLMGateway] Retryable error ({llm_err.code}), attempt {attempts}/{self.max_retries}. Backoff {delay:.2f}s...")
                await asyncio.sleep(delay)
            except Exception as e:
                # Bắt lỗi không lường trước
                err_msg = str(e)
                logger.error(f"[LLMGateway] Unexpected error: {err_msg}")
                raise LLMProviderError(f"Unexpected gateway error: {err_msg}", retryable=False)

        if last_error:
            raise last_error
        raise LLMProviderError("Exceeded maximum retries without a result.")


def get_llm_gateway(provider: Optional[BaseLLMProvider] = None) -> LLMGateway:
    """Factory helper để khởi tạo LLMGateway."""
    return LLMGateway(provider=provider)
