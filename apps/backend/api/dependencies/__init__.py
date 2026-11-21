"""FastAPI dependencies shared by every router."""
from apps.backend.api.dependencies.auth import AdminUser, CurrentUser, admin_user, current_user
from apps.backend.api.dependencies.database import DbSession, get_db

__all__ = ["AdminUser", "CurrentUser", "DbSession", "admin_user", "current_user", "get_db"]
