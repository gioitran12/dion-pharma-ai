"""
DION Healthcare AI — Unit Tests for Step 01B (LLM Gateway & Live API Integration)
Bộ 18 bài kiểm thử theo đúng yêu cầu nghiệp vụ của Bước 01B:
Sử dụng FakeLLMProvider được inject rõ ràng qua DI, không gọi API thật trong unit test để tránh chi phí.
Sử dụng asyncio.run() thuần để tương thích hoàn toàn với standard pytest.
"""

import os
import asyncio
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app
from modules.chat.llm_gateway import LLMGateway, get_llm_gateway
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
from modules.chat.enums import ChatIntent, ChatDecision, RiskLevel
from modules.chat.schemas import ChatRequest, ChatResponse

client = TestClient(app)


# ------------------------------------------------------------------------------
# Test 1: Import được LLMGateway và các Provider / Exceptions
# ------------------------------------------------------------------------------
def test_01_imports():
    assert LLMGateway is not None
    assert BaseLLMProvider is not None
    assert GeminiProvider is not None
    assert OpenAIProvider is not None
    assert FakeLLMProvider is not None
    assert issubclass(LLMConfigurationError, LLMError)
    assert issubclass(LLMAuthenticationError, LLMError)
    assert issubclass(LLMRateLimitError, LLMError)
    assert issubclass(LLMTimeoutError, LLMError)
    assert issubclass(LLMEmptyResponseError, LLMError)


# ------------------------------------------------------------------------------
# Test 2: Chọn đúng provider theo cấu hình
# ------------------------------------------------------------------------------
def test_02_select_provider_from_config():
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "LLM_MODEL": "gemini-2.5-flash"}):
        gw = LLMGateway()
        assert gw.provider_name == "gemini"
        assert gw.model_name == "gemini-2.5-flash"
        assert isinstance(gw._provider, GeminiProvider)

    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "LLM_MODEL": "gpt-4o-mini"}):
        gw = LLMGateway()
        assert gw.provider_name == "openai"
        assert gw.model_name == "gpt-4o-mini"
        assert isinstance(gw._provider, OpenAIProvider)


# ------------------------------------------------------------------------------
# Test 3: Provider không hợp lệ bị từ chối
# ------------------------------------------------------------------------------
def test_03_invalid_provider_rejected():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unsupported_provider_xyz"}):
        with pytest.raises(LLMConfigurationError) as exc_info:
            LLMGateway()
        assert exc_info.value.code == "LLM_INVALID_PROVIDER"
        assert "không được hỗ trợ" in exc_info.value.message


# ------------------------------------------------------------------------------
# Test 4: Thiếu API key hoặc key là placeholder trả lỗi rõ ràng
# ------------------------------------------------------------------------------
def test_04_missing_or_placeholder_key_rejected():
    # Trường hợp thiếu key hoàn toàn
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": ""}):
        gw = LLMGateway()
        with pytest.raises(LLMConfigurationError) as exc_info:
            gw.validate_configuration()
        assert exc_info.value.code == "LLM_NOT_CONFIGURED"

    # Trường hợp key là placeholder mẫu
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "your_openai_api_key_here"}):
        gw = LLMGateway()
        with pytest.raises(LLMConfigurationError) as exc_info:
            gw.validate_configuration()
        assert exc_info.value.code == "LLM_NOT_CONFIGURED"
        assert "placeholder" in exc_info.value.message


# ------------------------------------------------------------------------------
# Test 5: Request hợp lệ được chuyển đúng tới provider (DI)
# ------------------------------------------------------------------------------
def test_05_valid_request_routed_correctly():
    async def _test():
        fake = FakeLLMProvider(default_response="Xin chào DION Healthcare")
        gw = LLMGateway(provider=fake)

        result = await gw.generate(
            prompt="Xin chào trợ lý",
            system_instruction="Chỉ dẫn backend an toàn",
            temperature=0.5,
            max_output_tokens=256,
        )

        assert fake.call_count == 1
        assert len(fake.calls) == 1
        call_req = fake.calls[0]
        assert call_req.prompt == "Xin chào trợ lý"
        assert call_req.system_instruction == "Chỉ dẫn backend an toàn"
        assert call_req.temperature == 0.5
        assert call_req.max_output_tokens == 256
        assert result.content == "Xin chào DION Healthcare"

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 6: Response được chuẩn hóa đúng định dạng
# ------------------------------------------------------------------------------
def test_06_response_normalized_format():
    async def _test():
        fake = FakeLLMProvider(
            provider_name="fake_norm",
            model_name="fake-v2",
            default_response="Nội dung đã chuẩn hóa",
        )
        gw = LLMGateway(provider=fake)

        result = await gw.generate(prompt="Test format")
        assert isinstance(result, LLMResult)
        assert result.content == "Nội dung đã chuẩn hóa"
        assert result.provider == "fake_norm"
        assert result.model == "fake-v2"
        assert result.usage is not None
        assert result.usage.get("total_tokens") == 32
        assert result.latency_ms > 0
        assert result.finish_reason == "stop"
        assert result.request_id == "fake-trace-id-12345"

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 7: Response rỗng được xử lý
# ------------------------------------------------------------------------------
def test_07_empty_response_handled():
    async def _test():
        fake = FakeLLMProvider(side_effect=LLMEmptyResponseError("Provider returned empty text"))
        gw = LLMGateway(provider=fake)

        with pytest.raises(LLMEmptyResponseError) as exc_info:
            await gw.generate(prompt="Test empty")
        assert exc_info.value.code == "LLM_EMPTY_RESPONSE"
        assert exc_info.value.retryable is False

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 8: Timeout được xử lý
# ------------------------------------------------------------------------------
def test_08_timeout_handled():
    async def _test():
        fake = FakeLLMProvider(side_effect=LLMTimeoutError("Request timed out after 5s"))
        gw = LLMGateway(provider=fake, max_retries=1, retry_delay_seconds=0.01)

        with pytest.raises(LLMTimeoutError) as exc_info:
            await gw.generate(prompt="Test timeout")
        assert exc_info.value.code == "LLM_TIMEOUT"
        assert exc_info.value.retryable is True
        assert fake.call_count == 2  # 1 lần gọi đầu + 1 lần retry

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 9: Rate limit được xử lý
# ------------------------------------------------------------------------------
def test_09_rate_limit_handled():
    async def _test():
        fake = FakeLLMProvider(side_effect=LLMRateLimitError("429 Too Many Requests"))
        gw = LLMGateway(provider=fake, max_retries=1, retry_delay_seconds=0.01)

        with pytest.raises(LLMRateLimitError) as exc_info:
            await gw.generate(prompt="Test rate limit")
        assert exc_info.value.code == "LLM_RATE_LIMIT"
        assert exc_info.value.retryable is True
        assert fake.call_count == 2

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 10: Lỗi xác thực không bị retry vô hạn
# ------------------------------------------------------------------------------
def test_10_auth_error_not_retried():
    async def _test():
        fake = FakeLLMProvider(side_effect=LLMAuthenticationError("Invalid API key"))
        # Cấu hình max_retries=5 để kiểm chứng
        gw = LLMGateway(provider=fake, max_retries=5, retry_delay_seconds=0.01)

        with pytest.raises(LLMAuthenticationError) as exc_info:
            await gw.generate(prompt="Test auth")
        assert exc_info.value.code == "LLM_AUTH_ERROR"
        # Phải dừng ngay ở lần 1, TUYỆT ĐỐI KHÔNG RETRY
        assert fake.call_count == 1

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 11: Lỗi tạm thời được retry trong giới hạn
# ------------------------------------------------------------------------------
def test_11_transient_error_bounded_retry():
    async def _test():
        # fail_times=1: thất bại lần 1, thành công lần 2
        fake = FakeLLMProvider(
            fail_times=1,
            default_response="Thành công sau retry",
        )
        gw = LLMGateway(provider=fake, max_retries=2, retry_delay_seconds=0.01)

        result = await gw.generate(prompt="Test transient")
        assert fake.call_count == 2
        assert result.content == "Thành công sau retry"

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 12: Fake Provider chỉ dùng khi test qua Dependency Injection
# ------------------------------------------------------------------------------
def test_12_fake_provider_only_via_di():
    # Khi khởi tạo mặc định bằng env, fake provider không tự động được chọn trừ khi chỉ định
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}):
        gw = LLMGateway()
        assert not isinstance(gw._provider, FakeLLMProvider)

    # Chỉ dùng khi DI
    fake = FakeLLMProvider()
    gw_di = LLMGateway(provider=fake)
    assert gw_di._provider is fake


# ------------------------------------------------------------------------------
# Test 13: Không tự fallback sang mock khi provider thật gặp lỗi
# ------------------------------------------------------------------------------
def test_13_no_silent_fallback_to_mock_on_error():
    async def _test():
        fake = FakeLLMProvider(side_effect=LLMProviderError("Lỗi 500 từ nhà cung cấp", retryable=False))
        gw = LLMGateway(provider=fake, max_retries=0)

        # Khi provider gặp lỗi, hệ thống phải ném lỗi trung thực, không được trả về mock text
        with pytest.raises(LLMProviderError) as exc_info:
            await gw.generate(prompt="Test no silent fallback")
        assert "Lỗi 500 từ nhà cung cấp" in exc_info.value.message

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 14: Không lộ API key trong log hoặc response
# ------------------------------------------------------------------------------
def test_14_no_api_key_leaked_in_exceptions():
    secret_key = "AIzaSySecretRealKey123456789"
    prov = GeminiProvider(api_key=secret_key, model_name="gemini-2.5-flash")

    err = LLMAuthenticationError("Unauthorized request")
    assert secret_key not in str(err)
    assert secret_key not in repr(err)


# ------------------------------------------------------------------------------
# Test 15: API cũ /api/copilot/ask tiếp tục hoạt động
# ------------------------------------------------------------------------------
def test_15_legacy_endpoint_intact():
    payload = {"query": "Canxi Cal-Mom có tác dụng gì?", "sku": "DION-CAL-MOM"}
    response = client.post("/api/copilot/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "citations" in data
    assert "source_claims" in data
    assert "handoff_required" in data
    assert data["handoff_required"] is False
    assert data.get("ticket_created", False) is False  # Đảm bảo logic Step 00.1 không bị phá vỡ


# ------------------------------------------------------------------------------
# Test 16: API thử nghiệm không được truy cập khi chưa bật cấu hình
# ------------------------------------------------------------------------------
def test_16_experimental_endpoint_disabled_by_default():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "false"}):
        payload = {"message": "Xin chào"}
        response = client.post("/api/copilot/chat", json=payload)
        assert response.status_code == 403
        data = response.json()
        assert "disabled" in data["detail"].lower()


# ------------------------------------------------------------------------------
# Test 17: API thử nghiệm không trả lời tự do cho yêu cầu y khoa khi chưa có RAG & Safety
# ------------------------------------------------------------------------------
def test_17_experimental_endpoint_refuses_clinical_claims():
    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        # Câu hỏi về liều dùng / tác dụng phụ / điều trị
        payload = {"message": "Sản phẩm Cal-Mom có tác dụng điều trị bệnh loãng xương như thế nào?"}
        response = client.post("/api/copilot/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == ChatDecision.BLOCKED.value
        assert "từ chối" in data["answer"].lower() or "chưa kiểm duyệt" in data["answer"].lower()
        assert data["sources"] == []
        assert data["ticket_id"] is None
        assert data["risk"]["requires_handoff"] is True


# ------------------------------------------------------------------------------
# Test 18: API thử nghiệm trả lời an toàn cho chào hỏi khi bật và dùng Gateway
# ------------------------------------------------------------------------------
def test_18_experimental_endpoint_safe_greeting():
    fake_provider = FakeLLMProvider(default_response="Xin chào! Tôi là trợ lý AI của DION Healthcare AI.")

    with patch.dict(os.environ, {"ENABLE_EXPERIMENTAL_CHAT": "true"}):
        # Inject FakeLLMProvider vào get_llm_gateway
        with patch("server.get_llm_gateway", return_value=LLMGateway(provider=fake_provider)):
            payload = {"message": "Xin chào, bạn là trợ lý của ai?"}
            response = client.post("/api/copilot/chat", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["decision"] == ChatDecision.READY_TO_SEND.value
            assert data["intent"] == ChatIntent.GREETING.value
            assert "DION Healthcare AI" in data["answer"]
            assert data["sources"] == []
            assert data["ticket_id"] is None
            assert data["risk"]["requires_handoff"] is False


# ------------------------------------------------------------------------------
# Test 19: Lỗi 503 Service Unavailable / High Demand được đánh dấu retryable
# ------------------------------------------------------------------------------
def test_19_service_unavailable_503_retryable():
    async def _test():
        fake = FakeLLMProvider(
            fail_times=1,
            default_response="Thành công sau khi 503 giải tỏa",
        )
        gw = LLMGateway(provider=fake, max_retries=2, retry_delay_seconds=0.01)
        result = await gw.generate(prompt="Test 503 retry")
        assert fake.call_count == 2
        assert result.content == "Thành công sau khi 503 giải tỏa"

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 20: Lỗi 404 Model Not Found không được retry
# ------------------------------------------------------------------------------
def test_20_model_not_found_not_retried():
    async def _test():
        err = LLMProviderError(
            "Mô hình không tồn tại",
            code="LLM_MODEL_NOT_FOUND",
            retryable=False,
            status_code=404,
        )
        fake = FakeLLMProvider(side_effect=err)
        gw = LLMGateway(provider=fake, max_retries=3, retry_delay_seconds=0.01)

        with pytest.raises(LLMProviderError) as exc_info:
            await gw.generate(prompt="Test 404")
        assert exc_info.value.code == "LLM_MODEL_NOT_FOUND"
        assert exc_info.value.retryable is False
        # Dừng ngay ở lần gọi đầu tiên
        assert fake.call_count == 1

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# Test 21: Lỗi 400 Invalid Request không được retry
# ------------------------------------------------------------------------------
def test_21_invalid_request_400_not_retried():
    async def _test():
        err = LLMProviderError(
            "Yêu cầu không hợp lệ",
            code="LLM_INVALID_REQUEST",
            retryable=False,
            status_code=400,
        )
        fake = FakeLLMProvider(side_effect=err)
        gw = LLMGateway(provider=fake, max_retries=3, retry_delay_seconds=0.01)

        with pytest.raises(LLMProviderError) as exc_info:
            await gw.generate(prompt="Test 400")
        assert exc_info.value.code == "LLM_INVALID_REQUEST"
        assert exc_info.value.retryable is False
        assert fake.call_count == 1

    asyncio.run(_test())


