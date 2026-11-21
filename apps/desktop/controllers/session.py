from typing import Any

from apps.desktop.services.backend import BackendService


class SessionController:
    def __init__(self, backend: BackendService) -> None:
        self.backend = backend
        self.role: str | None = None

    @property
    def token(self) -> str | None:
        return self.backend.token

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def set_backend_url(self, url: str) -> None:
        self.backend.set_backend_url(url)

    def register(self, name: str, email: str, password: str) -> Any:
        return self.backend.register(name, email, password)

    def login(self, email: str, password: str) -> Any:
        return self.backend.login(email, password)

    def apply(self, result: dict[str, Any]) -> None:
        self.backend.set_token(result["access_token"])
        self.role = result["role"]

    def logout(self) -> Any:
        return self.backend.logout()

    def clear(self) -> None:
        self.backend.set_token(None)
        self.role = None

    def delete_account(self, password: str) -> Any:
        return self.backend.delete_account(password)

    def create_recovery_code(self, password: str) -> Any:
        return self.backend.create_recovery_code(password)

    def reset_password(self, email: str, recovery_code: str, password: str) -> Any:
        return self.backend.reset_password(email, recovery_code, password)
