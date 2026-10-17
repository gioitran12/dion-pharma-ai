"""
DION Healthcare AI — Fake LLM Provider (Test Only)
Dùng riêng cho Unit Test thông qua Dependency Injection.
KHÔNG ĐƯỢC tự động kích hoạt trong môi trường thực tế khi gọi API thất bại.
"""

from typing import Optional, List, Dict
from modules.chat.providers.base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResult,
    LLMError,
)


class FakeLLMProvider(BaseLLMProvider):
    """
    Fake Provider hỗ trợ mô phỏng phản hồi, lỗi mạng, lỗi xác thực, timeout
    và đếm số lần gọi để kiểm thử unit test độc lập với API thật.
    """

    def __init__(
        self,
        provider_name: str = "fake",
        model_name: str = "fake-model-v1",
        default_response: str = "Phản hồi giả lập từ FakeLLMProvider.",
        side_effect: Optional[Exception] = None,
        fail_times: int = 0,
        configured: bool = True,
    ):
        super().__init__(provider_name=provider_name, model_name=model_name)
        self.default_response = default_response
        self.side_effect = side_effect
        self.fail_times = fail_times
        self.configured = configured

        self.calls: List[LLMRequest] = []
        self.call_count: int = 0

    def validate_configuration(self) -> None:
        """Mô phỏng kiểm tra cấu hình."""
        if not self.configured:
            from modules.chat.providers.base import LLMConfigurationError
            raise LLMConfigurationError("FakeProvider: Chưa cấu hình key.", code="LLM_NOT_CONFIGURED")

    async def generate(self, request: LLMRequest) -> LLMResult:
        """Ghi nhận request và sinh kết quả hoặc ném exception."""
        self.call_count += 1
        self.calls.append(request)

        # Mô phỏng lỗi fail_times lần đầu trước khi thành công (kiểm thử retry)
        if self.fail_times > 0 and self.call_count <= self.fail_times:
            if self.side_effect:
                raise self.side_effect
            from modules.chat.providers.base import LLMProviderError
            raise LLMProviderError("Mô phỏng lỗi tạm thời", retryable=True)

        # Mô phỏng lỗi cố định
        if self.side_effect and self.fail_times == 0:
            raise self.side_effect

        return LLMResult(
            content=self.default_response,
            provider=self.provider_name,
            model=self.model_name,
            usage={"prompt_tokens": 12, "completion_tokens": 20, "total_tokens": 32},
            latency_ms=15.0,
            finish_reason="stop",
            request_id="fake-trace-id-12345",
        )
