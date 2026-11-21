import re
import httpx
import base64
from abc import ABC, abstractmethod

from backend.config import settings

class AIProviderError(RuntimeError):
    pass

class AIProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    def generate_with_image(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        raise AIProviderError("This provider does not support image review.")

    def status(self) -> dict:
        return {"configured": True, "reachable": None}

class GeminiProvider(AIProvider):
    def __init__(self):
        self.model = settings.gemini_model

    def api_key(self) -> str | None:
        return settings.gemini_api_key

    def status(self) -> dict:
        configured = bool(self.api_key() and re.fullmatch(r"gemini-[a-zA-Z0-9_.-]+", self.model))
        return {"configured": configured, "reachable": None}

    def _generate_content(self, parts: list[dict]) -> str:
        api_key = self.api_key()
        if not api_key or not self.status()["configured"]:
            raise AIProviderError("Set GEMINI_API_KEY and a supported GEMINI_MODEL on the backend.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": api_key},
                json={"contents": [{"parts": parts}], "generationConfig": {"maxOutputTokens": 4096}},
                timeout=httpx.Timeout(30, connect=5),
            )
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                raise AIProviderError("Gemini returned no generated candidate.")
            parts = candidates[0].get("content", {}).get("parts") or []
            text = "\n".join(
                part["text"].strip() for part in parts
                if isinstance(part, dict) and not part.get("thought")
                and isinstance(part.get("text"), str) and part["text"].strip()
            )
            if not text:
                raise AIProviderError("Gemini returned an invalid or empty response.")
            return text
        except AIProviderError:
            raise
        except httpx.TimeoutException:
            raise AIProviderError("Gemini timed out. Try again later.") from None
        except (httpx.HTTPError, AttributeError, KeyError, IndexError, TypeError, ValueError):
            raise AIProviderError("Gemini request failed or returned an invalid response.") from None

    def generate(self, prompt: str) -> str:
        return self._generate_content([{"text": prompt}])

    def generate_with_image(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        if not image_bytes:
            raise AIProviderError("Portfolio image content is empty.")
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return self._generate_content([
            {"text": prompt},
            {"inlineData": {"mimeType": mime_type, "data": encoded}},
        ])

class SkillBridgeProvider(AIProvider):
    def generate(self, prompt: str) -> str:
        raise AIProviderError("The proprietary SkillBridge AI model has not been trained or deployed.")

    def status(self) -> dict:
        return {"configured": False, "reachable": None}

class AIService:
    def __init__(self):
        self.providers = {
            "gemini": GeminiProvider(),
            "skillbridge": SkillBridgeProvider(),
        }
        self.active = settings.ai_provider

    def generate(self, prompt: str) -> str:
        provider = self.providers.get(self.active)
        if provider is None:
            raise AIProviderError("No AI provider is configured.")
        return provider.generate(prompt)

    def generate_with_image(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        provider = self.providers.get(self.active)
        if provider is None:
            raise AIProviderError("No AI provider is configured.")
        return provider.generate_with_image(prompt, image_bytes, mime_type)

    def status(self) -> dict:
        provider = self.providers.get(self.active)
        if provider is None:
            return {"configured": False, "reachable": None}
        status = provider.status()
        return {"provider": self.active, **status}
