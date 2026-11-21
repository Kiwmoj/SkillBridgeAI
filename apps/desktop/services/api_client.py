from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from apps.desktop.config.settings import DesktopSettings


class ApiError(RuntimeError):
    pass


class ApiClient:
    API_PREFIX = "/api/v1"

    def __init__(self, base_url: str, settings: DesktopSettings | None = None) -> None:
        self.settings = settings or DesktopSettings(backend_url=base_url)
        self.token: str | None = None
        self._base_url = ""
        self.set_backend_url(base_url)

    @property
    def base_url(self) -> str:
        return self._base_url

    def set_backend_url(self, value: str) -> None:
        url = value.strip().rstrip("/")
        try:
            parts = urlsplit(url)
            _port = parts.port
        except ValueError as exc:
            raise ApiError("Enter a valid backend URL.") from exc
        local = parts.hostname in {"127.0.0.1", "::1", "localhost"}
        if (not parts.hostname or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or "\\" in url or any(c.isspace() for c in url)
                or not (parts.scheme == "https" or (local and parts.scheme == "http"))):
            raise ApiError("Use HTTPS for a remote backend, or HTTP for a local loopback backend.")
        if self.token is not None and url != self._base_url:
            raise ApiError("Sign out before changing the backend.")
        self._base_url = url

    def set_token(self, token: str | None) -> None:
        self.token = token

    def _request(self, method: str, path: str, timeout: float | None = None, authenticated: bool = True,
                 **kwargs: Any) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Expected a backend API path.")
        if timeout is None:
            timeout = self.settings.request_timeout
        headers = {"Authorization": f"Bearer {self.token}"} if self.token and authenticated else {}
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=5), trust_env=False) as client:
                response = client.request(method, self.base_url + self.API_PREFIX + path, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise ApiError("The backend took too long to respond. Check the action before retrying.") from exc
        except httpx.RequestError as exc:
            raise ApiError("Cannot reach the backend. Check that it is running and that the address is correct.") from exc
        if not response.is_success:
            message = f"Backend returned HTTP {response.status_code}."
            try:
                data = response.json()
            except ValueError:
                data = None
            detail = data.get("detail") if isinstance(data, dict) else None
            if isinstance(detail, str):
                message = detail
            elif isinstance(detail, list):
                errors = [f"{'.'.join(map(str, item.get('loc', [])[1:]))}: {item['msg']}"
                          for item in detail if isinstance(item, dict) and isinstance(item.get("msg"), str)]
                if errors:
                    message = "\n".join(errors)
            if response.status_code == 401 and self.token and authenticated:
                message += " Sign out and sign in again if your session expired."
            raise ApiError(message)
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("The backend returned an invalid response.") from exc

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def put(self, path: str, json: Any = None) -> Any:
        return self._request("PUT", path, json=json)

    def post(self, path: str, json: Any = None, *, authenticated: bool = True) -> Any:
        return self._request("POST", path, authenticated=authenticated, json=json)

    def patch(self, path: str, json: Any) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def upload(self, path: str, file_path: str, timeout: float, params: dict[str, Any] | None = None) -> Any:
        source = Path(file_path)
        with source.open("rb") as stream:
            return self._request("POST", path, timeout=timeout, params=params, files={"file": (source.name, stream)})
