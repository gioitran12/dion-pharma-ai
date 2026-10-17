"""
DION Healthcare AI — Live LLM Gateway Smoke Test (Bước 01B)
Script kiểm thử kết nối API LLM thật (Gemini / OpenAI).
Chỉ chạy thủ công khi người dùng đã cấu hình API key hợp lệ trong .env.
Tuyệt đối KHÔNG in API key trong console/log.
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo import được các module từ thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

# Tải biến môi trường từ .env
load_dotenv(ROOT_DIR / ".env")



from modules.chat.llm_gateway import LLMGateway
from modules.chat.providers.base import (
    LLMConfigurationError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMError,
)


async def run_smoke_test():
    print("=" * 70)
    print("   DION HEALTHCARE AI — LIVE LLM GATEWAY SMOKE TEST (STEP 01B)")
    print("=" * 70)

    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    model_name = os.getenv("LLM_MODEL") or ("gemini-2.5-flash" if provider_name == "gemini" else "gpt-4o-mini")

    print(f"[*] Cấu hình mục tiêu:")
    print(f"    - Provider: {provider_name}")
    print(f"    - Model:    {model_name}")
    print(f"    - Timeout:  {os.getenv('LLM_TIMEOUT_SECONDS', '20')}s")

    # Kiểm tra API Key có tồn tại và không phải placeholder
    key_var = "GEMINI_API_KEY" if provider_name == "gemini" else "OPENAI_API_KEY"
    api_key = os.getenv(key_var, "").strip()

    if not api_key:
        print(f"\n[!] TRẠNG THÁI: BLOCKED_FOR_LIVE_VERIFICATION")
        print(f"[!] Lý do: Biến môi trường {key_var} chưa được thiết lập.")
        print(f"    Vui lòng bổ sung {key_var}=<your_key> vào file .env và chạy lại.")
        sys.exit(2)

    lowered_key = api_key.lower()
    if "your_" in lowered_key or "placeholder" in lowered_key or "example" in lowered_key:
        print(f"\n[!] TRẠNG THÁI: BLOCKED_FOR_LIVE_VERIFICATION")
        print(f"[!] Lý do: {key_var} đang chứa giá trị placeholder mẫu ('{api_key[:8]}...').")
        print(f"    Vui lòng thay thế bằng API key thực tế trong file .env để thực hiện smoke test.")
        sys.exit(2)

    print(f"[*] Đã phát hiện {key_var} (Độ dài: {len(api_key)} ký tự, đã mã hóa an toàn).")
    print(f"[*] Đang khởi tạo LLMGateway...")

    try:
        gateway = LLMGateway(provider_name=provider_name, model_name=model_name)
        gateway.validate_configuration()
    except LLMConfigurationError as e:
        print(f"\n[FAIL] Lỗi cấu hình LLMGateway: {e.message} (Code: {e.code})")
        sys.exit(1)

    # Prompt thử nghiệm an toàn, ngắn gọn
    test_prompt = "Xin chào. Hãy xác nhận bạn là trợ lý của hệ thống DION Healthcare AI bằng một câu ngắn gọn."
    print(f"\n[*] Gửi prompt thử nghiệm: \"{test_prompt}\"")
    print("[*] Đang gửi yêu cầu tới API của nhà cung cấp...")

    start_perf = time.perf_counter()
    try:
        result = await gateway.generate(
            prompt=test_prompt,
            system_instruction="Bạn là trợ lý AI nội bộ của DION Healthcare AI. Trả lời súc tích bằng tiếng Việt.",
            max_output_tokens=100,
        )
        total_time_ms = round((time.perf_counter() - start_perf) * 1000, 2)

        print("\n" + "=" * 70)
        print("   KẾT QUẢ KIỂM THỬ THÀNH CÔNG (LIVE API VERIFIED)")
        print("=" * 70)
        print(f"Provider:       {result.provider}")
        print(f"Model:          {result.model}")
        print(f"Gateway Latency:{result.latency_ms} ms (Tổng: {total_time_ms} ms)")
        print(f"Finish Reason:  {result.finish_reason}")
        print(f"Request/Trace:  {result.request_id or 'N/A'}")
        if result.usage:
            print(f"Token Usage:    Prompt={result.usage.get('prompt_tokens')}, "
                  f"Completion={result.usage.get('completion_tokens')}, "
                  f"Total={result.usage.get('total_tokens')}")
        print(f"\nPhản hồi từ mô hình:\n\"\"\"\n{result.content}\n\"\"\"")
        print("=" * 70)
        print("[SUCCESS] Live LLM API hoạt động hoàn hảo và sẵn sàng tích hợp.")
        sys.exit(0)

    except LLMAuthenticationError as e:
        print(f"\n[FAIL] Lỗi xác thực API ({e.code}): {e.message}")
        print("       Vui lòng kiểm tra lại tính hợp lệ của API key.")
        sys.exit(1)
    except LLMRateLimitError as e:
        print(f"\n[FAIL] Lỗi vượt quá hạn mức ({e.code}): {e.message}")
        sys.exit(1)
    except LLMTimeoutError as e:
        print(f"\n[FAIL] Lỗi Timeout ({e.code}): {e.message}")
        sys.exit(1)
    except LLMError as e:
        print(f"\n[FAIL] Lỗi LLM ({e.code}): {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Lỗi không xác định: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
