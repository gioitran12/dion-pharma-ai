"""
DION Healthcare AI — Base LLM Provider & Gateway Models
Định nghĩa các interface trừu tượng, request/response models nội bộ và hệ thống Exception chuẩn cho LLM Gateway.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ==============================================================================
# EXCEPTIONS
# ==============================================================================

class LLMError(Exception):
    """Lớp Exception cơ sở cho tất cả lỗi phát sinh từ LLM Gateway."""
    def __init__(self, message: str, code: str = "LLM_ERROR", retryable: bool = False, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code='{self.code}', retryable={self.retryable}, message='{self.message}')"


class LLMConfigurationError(LLMError):
    """Lỗi cấu hình: thiếu biến môi trường, thiếu API key, hoặc cấu hình provider không hợp lệ."""
    def __init__(self, message: str, code: str = "LLM_NOT_CONFIGURED"):
        super().__init__(message=message, code=code, retryable=False, status_code=500)


class LLMAuthenticationError(LLMError):
    """Lỗi xác thực API key: API key không hợp lệ, hết hạn hoặc không có quyền truy cập."""
    def __init__(self, message: str = "Invalid or unauthorized API key."):
        super().__init__(message=message, code="LLM_AUTH_ERROR", retryable=False, status_code=401)


class LLMRateLimitError(LLMError):
    """Lỗi vượt quá hạn mức request/token của provider."""
    def __init__(self, message: str = "Rate limit exceeded by LLM provider."):
        super().__init__(message=message, code="LLM_RATE_LIMIT", retryable=True, status_code=429)


class LLMTimeoutError(LLMError):
    """Lỗi timeout khi gọi API nhà cung cấp."""
    def __init__(self, message: str = "Request to LLM provider timed out."):
        super().__init__(message=message, code="LLM_TIMEOUT", retryable=True, status_code=504)


class LLMEmptyResponseError(LLMError):
    """Lỗi nhà cung cấp trả về nội dung rỗng hoặc không có candidate."""
    def __init__(self, message: str = "LLM provider returned empty response."):
        super().__init__(message=message, code="LLM_EMPTY_RESPONSE", retryable=False, status_code=502)


class LLMProviderError(LLMError):
    """Lỗi từ phía provider (server error 5xx, network error, hoặc model không tồn tại)."""
    def __init__(self, message: str, code: str = "LLM_PROVIDER_ERROR", retryable: bool = True, status_code: int = 502):
        super().__init__(message=message, code=code, retryable=retryable, status_code=status_code)


# ==============================================================================
# INTERNAL GATEWAY REQUEST & RESPONSE MODELS
# ==============================================================================

class LLMMessage(BaseModel):
    """Cấu trúc một tin nhắn trong ngữ cảnh gửi tới LLM."""
    role: str = Field(..., description="Vai trò: 'system', 'user', hoặc 'assistant'")
    content: str = Field(..., description="Nội dung tin nhắn")


class LLMRequest(BaseModel):
    """Request nội bộ chuẩn hóa gửi tới LLM Provider."""
    prompt: Optional[str] = Field(None, description="Câu hỏi hoặc lệnh đơn giản nếu không truyền messages")
    messages: Optional[List[LLMMessage]] = Field(None, description="Danh sách lịch sử hội thoại")
    system_instruction: Optional[str] = Field(None, description="System instructions quản lý bởi backend")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Độ ngẫu nhiên")
    max_output_tokens: Optional[int] = Field(512, ge=1, le=4096, description="Giới hạn tokens sinh ra")
    timeout_seconds: Optional[float] = Field(20.0, gt=0, description="Thời gian timeout tính bằng giây")
    stop_sequences: Optional[List[str]] = Field(None, description="Các chuỗi dừng sinh")

    def get_full_prompt_text(self) -> str:
        """Helper lấy nội dung prompt chính nếu chỉ có prompt hoặc lấy message cuối."""
        if self.prompt:
            return self.prompt
        if self.messages:
            for msg in reversed(self.messages):
                if msg.role == "user":
                    return msg.content
        return ""


class LLMResult(BaseModel):
    """Kết quả phản hồi chuẩn hóa trả về từ LLM Gateway."""
    content: str = Field(..., description="Nội dung câu trả lời từ mô hình")
    provider: str = Field(..., description="Tên nhà cung cấp (gemini, openai, fake...)")
    model: str = Field(..., description="Tên model đã thực thi")
    usage: Optional[Dict[str, int]] = Field(None, description="Thống kê tokens: prompt_tokens, completion_tokens, total_tokens")
    latency_ms: float = Field(0.0, description="Thời gian phản hồi tính bằng mili-giây")
    finish_reason: Optional[str] = Field(None, description="Lý do kết thúc sinh: stop, length, safety...")
    request_id: Optional[str] = Field(None, description="Trace ID hoặc Request ID từ provider")


# ==============================================================================
# BASE LLM PROVIDER INTERFACE
# ==============================================================================

class BaseLLMProvider(ABC):
    """Interface cơ sở cho các nhà cung cấp LLM cụ thể."""

    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResult:
        """Thực hiện gọi API LLM và trả về LLMResult chuẩn hóa."""
        pass

    @abstractmethod
    def validate_configuration(self) -> None:
        """Kiểm tra API key và thông số cấu hình. Ném LLMConfigurationError nếu không hợp lệ."""
        pass
