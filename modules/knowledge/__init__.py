"""
DION Healthcare AI — Knowledge Module Package
Cung cấp Product Knowledge Hub, Data Models và Claim Eligibility Validator cho phân hệ AI Chatbot.
"""

from modules.knowledge.schemas import (
    KnowledgeZone,
    ClaimStatus,
    ValidationCode,
    ProductRecord,
    ClaimRecord,
    ClaimValidationResult,
    ValidationSeverity,
    DataValidationItem,
    DataValidationSummary,
)

from modules.knowledge.validator import (
    ClaimEligibilityValidator,
    validate_claim_eligibility,
)

from modules.knowledge.repository import (
    BaseKnowledgeRepository,
    JSONKnowledgeRepository,
    get_knowledge_repository,
)

__all__ = [
    # Enums
    "KnowledgeZone",
    "ClaimStatus",
    "ValidationCode",
    "ValidationSeverity",
    # Models
    "ProductRecord",
    "ClaimRecord",
    "ClaimValidationResult",
    "DataValidationItem",
    "DataValidationSummary",
    # Validator
    "ClaimEligibilityValidator",
    "validate_claim_eligibility",
    # Repository
    "BaseKnowledgeRepository",
    "JSONKnowledgeRepository",
    "get_knowledge_repository",
]
