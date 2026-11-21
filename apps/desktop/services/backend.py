from typing import Any

from apps.desktop.config.settings import DesktopSettings
from apps.desktop.services.api_client import ApiClient


class BackendService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client

    @property
    def settings(self) -> DesktopSettings:
        return self.client.settings

    @property
    def base_url(self) -> str:
        return self.client.base_url

    def set_backend_url(self, value: str) -> None:
        self.client.set_backend_url(value)

    @property
    def token(self) -> str | None:
        return self.client.token

    def set_token(self, token: str | None) -> None:
        self.client.set_token(token)

    def health(self) -> Any:
        return self.client.get("/health")

    def register(self, name: str, email: str, password: str) -> Any:
        return self.client.post("/auth/register", {"name": name, "email": email, "password": password},
                                authenticated=False)

    def login(self, email: str, password: str) -> Any:
        return self.client.post("/auth/login", {"email": email, "password": password}, authenticated=False)

    def logout(self) -> Any:
        return self.client.post("/auth/logout")

    def me(self) -> Any:
        return self.client.get("/auth/me")

    def create_recovery_code(self, password: str) -> Any:
        return self.client.post("/auth/recovery-code", {"password": password})

    def reset_password(self, email: str, recovery_code: str, password: str) -> Any:
        return self.client.post("/auth/reset-password", {
            "email": email, "recovery_code": recovery_code, "password": password,
        })

    def delete_account(self, password: str) -> Any:
        return self.client.post("/auth/delete-account", {"password": password})

    def get_profile(self) -> Any:
        return self.client.get("/profile")

    def update_profile(self, payload: dict[str, Any]) -> Any:
        return self.client.put("/profile", payload)

    def search_occupations(self, q: str) -> Any:
        return self.client.get("/occupations/search", {"q": q})

    def occupation_detail(self, occupation_id: int | str, category: str | None = None,
                          limit: int | None = None) -> Any:
        params: dict[str, Any] = {}
        if category is not None:
            params["category"] = category
        if limit is not None:
            params["limit"] = limit
        return self.client.get(f"/occupations/{occupation_id}", params or None)

    def saved_careers(self) -> Any:
        return self.client.get("/occupations/saved")

    def save_career(self, occupation_id: int | str) -> Any:
        return self.client.put(f"/occupations/saved/{occupation_id}")

    def compare_occupations(self, occupation_ids: list[int]) -> Any:
        return self.client.post("/occupations/compare", {"occupation_ids": occupation_ids})

    def create_custom_occupation(self, payload: dict[str, Any]) -> Any:
        return self.client.post("/custom-occupations", payload)

    def custom_occupations(self) -> Any:
        return self.client.get("/custom-occupations")

    def generate_guidance(self, purpose: str, question: str) -> Any:
        return self.client.post("/ai/generate", {"purpose": purpose, "question": question})

    def skill_gap(self, payload: dict[str, Any]) -> Any:
        return self.client.post("/skill-gap", payload)

    def create_roadmap(self, payload: dict[str, Any]) -> Any:
        return self.client.post("/roadmaps", payload)

    def roadmaps(self) -> Any:
        return self.client.get("/roadmaps")

    def activities(self) -> Any:
        return self.client.get("/activities")

    def create_activity(self, payload: dict[str, Any]) -> Any:
        return self.client.post("/activities", payload)

    def update_activity(self, activity_id: int | str, payload: dict[str, Any]) -> Any:
        return self.client.patch(f"/activities/{activity_id}", payload)

    def upload_portfolio(self, file_path: str) -> Any:
        return self.client.upload("/portfolio/upload", file_path, self.settings.upload_timeout)

    def portfolio_items(self) -> Any:
        return self.client.get("/portfolio")

    def evaluate_portfolio(self, item_id: int | str) -> Any:
        return self.client.post(f"/portfolio/{item_id}/evaluate", {"send_to_provider": True})

    def create_project(self, payload: dict[str, Any]) -> Any:
        return self.client.post("/projects", payload)

    def projects(self) -> Any:
        return self.client.get("/projects")

    def update_project(self, project_id: int | str, status: str) -> Any:
        return self.client.patch(f"/projects/{project_id}", {"status": status})

    def find_opportunities(self, q: str) -> Any:
        return self.client.get("/opportunities", {"q": q})

    def save_opportunity(self, item: dict[str, Any]) -> Any:
        return self.client.post("/opportunities/save", item)

    def saved_opportunities(self) -> Any:
        return self.client.get("/opportunities/saved")

    def update_opportunity(self, opportunity_id: int | str, status: str) -> Any:
        return self.client.patch(f"/opportunities/saved/{opportunity_id}", {"application_status": status})

    def progress(self) -> Any:
        return self.client.get("/progress")

    def training_consent(self) -> Any:
        return self.client.get("/training-consent")

    def update_training_consent(self, enabled: bool) -> Any:
        return self.client.put("/training-consent", {"consent_enabled": enabled})

    def submit_contribution(self, payload: dict[str, Any]) -> Any:
        return self.client.post("/contributions", payload)

    def my_contributions(self) -> Any:
        return self.client.get("/contributions")

    def set_contribution_consent(self, contribution_id: int | str, enabled: bool) -> Any:
        return self.client.put(f"/contributions/{contribution_id}/consent", {"consent_enabled": enabled})

    def admin_dashboard(self) -> Any:
        return self.client.get("/admin/dashboard")

    def admin_contributions(self) -> Any:
        return self.client.get("/admin/contributions")

    def review_contribution(self, contribution_id: int | str, payload: dict[str, Any]) -> Any:
        return self.client.post(f"/admin/contributions/{contribution_id}/review", payload)

    def contribution_history(self, contribution_id: int | str) -> Any:
        return self.client.get(f"/admin/contributions/{contribution_id}/history")

    def import_onet(self, file_path: str, version: str) -> Any:
        return self.client.upload("/admin/onet/import", file_path, self.settings.import_timeout,
                                  params={"version": version})

    def build_dataset(self, name: str) -> Any:
        return self.client.post("/admin/datasets/build", {"name": name})

    def datasets(self) -> Any:
        return self.client.get("/admin/datasets")

    def training_history(self) -> Any:
        return self.client.get("/admin/training/history")

    def models(self) -> Any:
        return self.client.get("/admin/models")
