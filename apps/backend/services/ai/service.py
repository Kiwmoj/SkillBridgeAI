"""The single entry point every AI-powered feature uses; providers are swapped by configuration."""
from apps.backend.core.config import settings
from apps.backend.services.ai.providers import AIProvider, AIProviderError, GeminiProvider, SkillBridgeProvider


class AIService:
    def __init__(self, providers: dict[str, AIProvider] | None = None, active: str | None = None):
        self.providers: dict[str, AIProvider] = providers or {
            "gemini": GeminiProvider(),
            "skillbridge": SkillBridgeProvider(),
        }
        self.active = active or settings.ai_provider

    def _provider(self) -> AIProvider:
        provider = self.providers.get(self.active)
        if provider is None:
            raise AIProviderError("No AI provider is configured.")
        return provider

    def generate(self, prompt: str) -> str:
        return self._provider().generate(prompt)

    def generate_with_image(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        return self._provider().generate_with_image(prompt, image_bytes, mime_type)

    def status(self) -> dict:
        provider = self.providers.get(self.active)
        if provider is None:
            return {"provider": self.active, "configured": False, "reachable": None}
        return {"provider": self.active, **provider.status()}


ai_service = AIService()
