import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str | None = None):
        load_dotenv()
        self.token: str | None = None
        self._base_url = ""
        self.set_backend_url(base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))

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

    def set_token(self, token: str | None):
        self.token = token

    def _request(self, method, path, timeout=45, authenticated=True, **kwargs):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Expected a backend API path.")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token and authenticated else {}
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=5), trust_env=False) as client:
                response = client.request(method, self.base_url + path, headers=headers, **kwargs)
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

    def register(self, name, email, password):
        return self._request("POST", "/auth/register", authenticated=False,
                             json={"name": name, "email": email, "password": password})

    def login(self, email, password):
        return self._request("POST", "/auth/login", authenticated=False, json={"email": email, "password": password})

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def put(self, path, json=None):
        return self._request("PUT", path, json=json)

    def post(self, path, json=None):
        return self._request("POST", path, json=json)

    def patch(self, path, json):
        return self._request("PATCH", path, json=json)

    def delete(self, path):
        return self._request("DELETE", path)

    def upload(self, path, file_path, params=None):
        source = Path(file_path)
        timeout = 600 if path == "/admin/onet/import" else 60
        with source.open("rb") as stream:
            return self._request("POST", path, timeout=timeout, params=params, files={"file": (source.name, stream)})
