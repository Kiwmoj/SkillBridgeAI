"""Provider-independent AI access: one service, pluggable providers, retrieval, and grounded generation."""
from apps.backend.services.ai.grounded import generate_from_image, generate_grounded
from apps.backend.services.ai.providers import AIProvider, AIProviderError, GeminiProvider, SkillBridgeProvider
from apps.backend.services.ai.retrieval import RetrievalService, hashed_embedding, retrieval_service, source_context
from apps.backend.services.ai.service import AIService, ai_service

__all__ = [
    "AIProvider", "AIProviderError", "AIService", "GeminiProvider", "RetrievalService", "SkillBridgeProvider",
    "ai_service", "generate_from_image", "generate_grounded", "hashed_embedding", "retrieval_service",
    "source_context",
]
