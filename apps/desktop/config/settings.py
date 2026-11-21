import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class DesktopSettings:
    backend_url: str
    request_timeout: float = 45
    upload_timeout: float = 60
    import_timeout: float = 600
    app_name: str = "SkillBridge AI"


def load_desktop_settings(backend_url: str | None = None) -> DesktopSettings:
    load_dotenv()
    return DesktopSettings(backend_url=backend_url or os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL))
