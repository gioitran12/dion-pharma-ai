"""
DION Healthcare AI — Google Gemini LLM Provider
Triển khai BaseLLMProvider sử dụng Google GenAI SDK chính thức (`google-genai`).
"""

import os
import time
import asyncio
from typing import Optional, Dict

from google import genai
from google.genai import types
from google.genai.errors import APIError

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


class GeminiProvider(BaseLLMProvider):
    """Provider cho Google Gemini sử dụng SDK google-genai mới nhất."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        client: Optional[genai.Client] = None,
    ):
        provider_name = "gemini"
        resolved_model = model_name or os.getenv("LLM_MODEL") or "gemini-2.5-flash"
        super().__init__(provider_name=provider_name, model_name=resolved_model)

        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._injected_client = client
        self._client: Optional[genai.Client] = client

    def validate_configuration(self) -> None:
        """Kiểm tra tính hợp lệ của API Key và cấu hình."""
        if self._injected_client is not None:
            return

        if not self._api_key or not self._api_key.strip():
            raise LLMConfigurationError(
                "GEMINI_API_KEY chưa được cấu hình. Vui lòng thiết lập biến môi trường GEMINI_API_KEY.",
                code="LLM_NOT_CONFIGURED"
            )

        # Kiểm tra nếu API key là placeholder mẫu
        lowered = self._api_key.strip().lower()
        if "your_" in lowered or "placeholder" in lowered or "example" in lowered:
            raise LLMConfigurationError(
                "GEMINI_API_KEY đang chứa giá trị mẫu (placeholder). Vui lòng cung cấp API key thật.",
                code="LLM_NOT_CONFIGURED"
            )

    def _get_client(self) -> genai.Client:
        """Khởi tạo client an toàn nếu chưa có."""
        if self._client is not None:
            return self._client
        self.validate_configuration()
        self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResult:
        """Gửi prompt tới Gemini và chuẩn hóa kết quả về LLMResult."""
        client = self._get_client()

        # Chuẩn bị system instruction và config
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            stop_sequences=request.stop_sequences,
        )

        # Chuẩn bị contents
        if request.messages and len(request.messages) > 0:
            contents = []
            for m in request.messages:
                role = "user" if m.role == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=m.content)],
                    )
                )
        else:
            prompt_text = request.get_full_prompt_text()
            if not prompt_text:
                raise LLMEmptyResponseError("Request prompt is empty.")
            contents = prompt_text

        timeout = request.timeout_seconds if request.timeout_seconds else 20.0
        start_time = time.perf_counter()

        try:
            # Gọi API bất đồng bộ với timeout kiểm soát
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise LLMTimeoutError(f"Gemini API request timed out after {timeout}s.")
        except APIError as e:
            err_code = getattr(e, "code", None)
            err_str = str(e)
            # Không để lộ API key trong exception message
            if self._api_key and self._api_key in err_str:
                err_str = err_str.replace(self._api_key, "[REDACTED_API_KEY]")

            # 1. Lỗi xác thực / phân quyền (401, 403) -> Tuyệt đối không retry
            if err_code in (401, 403) or "API_KEY_INVALID" in err_str or "PERMISSION_DENIED" in err_str:
                raise LLMAuthenticationError("Gemini API key không hợp lệ hoặc không có quyền truy cập.")

            # 2. Lỗi Model không tồn tại (404) -> Tuyệt đối không retry
            elif err_code == 404 or "NOT_FOUND" in err_str:
                raise LLMProviderError(
                    f"Mô hình Gemini '{self.model_name}' không tồn tại hoặc đã ngừng hỗ trợ. Vui lòng kiểm tra lại cấu hình LLM_MODEL.",
                    code="LLM_MODEL_NOT_FOUND",
                    retryable=False,
                    status_code=404,
                )

            # 3. Lỗi yêu cầu client sai (400) -> Tuyệt đối không retry
            elif err_code == 400 or "INVALID_ARGUMENT" in err_str:
                raise LLMProviderError(
                    "Yêu cầu gửi tới Gemini không hợp lệ. Vui lòng kiểm tra lại tham số cấu hình.",
                    code="LLM_INVALID_REQUEST",
                    retryable=False,
                    status_code=400,
                )

            # 4. Lỗi giới hạn tần suất yêu cầu (429) -> Có retry (exponential backoff)
            elif err_code == 429 or "RESOURCE_EXHAUSTED" in err_str:
                raise LLMRateLimitError(
                    "Dịch vụ AI đang tạm thời đạt giới hạn tần suất yêu cầu (Rate Limit). Vui lòng thử lại sau giây lát."
                )

            # 5. Lỗi quá tải / tạm thời không khả dụng (503 / UNAVAILABLE / high demand) -> Có retry
            elif err_code == 503 or "UNAVAILABLE" in err_str or "high demand" in err_str.lower():
                raise LLMProviderError(
                    "Dịch vụ AI (Gemini) hiện đang có lưu lượng truy cập cao và tạm thời không khả dụng. Vui lòng thử lại sau giây lát.",
                    code="LLM_SERVICE_UNAVAILABLE",
                    retryable=True,
                    status_code=503,
                )

            # 6. Lỗi Timeout từ Gateway/Server (504) -> Có retry
            elif err_code == 504:
                raise LLMTimeoutError(
                    "Yêu cầu tới dịch vụ AI bị quá thời gian chờ (Gateway Timeout). Vui lòng thử lại sau giây lát."
                )

            # 7. Lỗi máy chủ khác từ nhà cung cấp (500, 502...) -> Có retry nếu 5xx
            else:
                retryable = err_code is not None and err_code >= 500
                friendly_msg = (
                    f"Dịch vụ AI gặp sự cố máy chủ tạm thời ({err_code or 502}). Vui lòng thử lại sau giây lát."
                    if retryable
                    else f"Dịch vụ AI phản hồi mã lỗi ({err_code or 'UNKNOWN'})."
                )
                raise LLMProviderError(
                    friendly_msg,
                    code="LLM_PROVIDER_ERROR",
                    retryable=retryable,
                    status_code=err_code or 502,
                )
        except Exception as e:
            if isinstance(e, (LLMConfigurationError, LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError, LLMEmptyResponseError, LLMProviderError)):
                raise e
            err_str = str(e)
            if self._api_key and self._api_key in err_str:
                err_str = err_str.replace(self._api_key, "[REDACTED_API_KEY]")
            if "timeout" in err_str.lower():
                raise LLMTimeoutError(f"Gemini request timed out: {err_str}")
            raise LLMProviderError(f"Unexpected Gemini error: {err_str}", retryable=False)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Trích xuất content
        text_content = ""
        finish_reason = None
        if hasattr(response, "text") and response.text:
            text_content = response.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            first_candidate = response.candidates[0]
            if hasattr(first_candidate, "finish_reason"):
                finish_reason = str(first_candidate.finish_reason)
            if hasattr(first_candidate, "content") and first_candidate.content:
                parts = getattr(first_candidate.content, "parts", [])
                text_content = "".join([p.text for p in parts if hasattr(p, "text") and p.text]).strip()

        if not text_content:
            raise LLMEmptyResponseError("Gemini returned an empty response or candidate.")

        # Trích xuất usage metadata nếu có
        usage_dict: Optional[Dict[str, int]] = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            usage_dict = {
                "prompt_tokens": getattr(meta, "prompt_token_count", 0) or 0,
                "completion_tokens": getattr(meta, "candidates_token_count", 0) or 0,
                "total_tokens": getattr(meta, "total_token_count", 0) or 0,
            }

        return LLMResult(
            content=text_content,
            provider=self.provider_name,
            model=self.model_name,
            usage=usage_dict,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            request_id=getattr(response, "response_id", None) or getattr(response, "id", None),
        )
