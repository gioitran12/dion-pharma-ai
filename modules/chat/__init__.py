"""
DION Healthcare AI — Chat Module Package
Cung cấp các Data Models, Pydantic Schemas, Enums và LLM Gateway cho phân hệ AI Chatbot & Sales Copilot.
"""

from modules.chat.enums import (
    ChatIntent,
    ChatDecision,
    RiskLevel,
    TicketStatus,
    ChatRole,
)

from modules.chat.schemas import (
    ChatRequest,
    ChatMessage,
    CitationInfo,
    IntentResult,
    SafetyResult,
    TicketData,
    ChatAction,
    ChatResponse,
    LegacyCopilotRequest,
    LegacyCopilotResponse,
    ErrorDetail,
    ChatErrorResponse,
    legacy_to_chat_response,
    chat_response_to_legacy,
)

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
from modules.chat.llm_gateway import LLMGateway, get_llm_gateway
from modules.chat.prompts.system_prompts import get_system_prompt
from modules.chat.question_understanding import (
    QuestionUnderstandingEngine,
    ProductResolutionResult,
    QuestionUnderstandingResult,
)
from modules.chat.claim_retriever import (
    ClaimRelevanceRetriever,
    RetrievedClaim,
)

__all__ = [
    # Question Understanding & Claim Retrieval
    "QuestionUnderstandingEngine",
    "ProductResolutionResult",
    "QuestionUnderstandingResult",
    "ClaimRelevanceRetriever",
    "RetrievedClaim",
    # Enums
    "ChatIntent",
    "ChatDecision",
    "RiskLevel",
    "TicketStatus",
    "ChatRole",
    # Schemas
    "ChatRequest",
    "ChatMessage",
    "CitationInfo",
    "IntentResult",
    "SafetyResult",
    "TicketData",
    "ChatAction",
    "ChatResponse",
    "LegacyCopilotRequest",
    "LegacyCopilotResponse",
    "ErrorDetail",
    "ChatErrorResponse",
    "legacy_to_chat_response",
    "chat_response_to_legacy",
    # LLM Gateway & Providers
    "LLMGateway",
    "get_llm_gateway",
    "BaseLLMProvider",
    "LLMRequest",
    "LLMResult",
    "LLMMessage",
    "LLMError",
    "LLMConfigurationError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMEmptyResponseError",
    "LLMProviderError",
    "GeminiProvider",
    "OpenAIProvider",
    "FakeLLMProvider",
    "get_system_prompt",
]
