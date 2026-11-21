"""Helpers for exercising the API through the test client."""
from sqlalchemy.orm import Session

from apps.backend.core.security import hash_password
from apps.backend.database import connection
from apps.backend.models import User

API = "/api/v1"
PASSWORD = "strong-password"


def register(client, name="Student", email="student@example.com", password=PASSWORD):
    response = client.post(f"{API}/auth/register", json={"name": name, "email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def admin_token(client, email="admin@example.com", password=PASSWORD) -> str:
    """Create (once) and sign in a server-provisioned administrator; registration cannot create admins."""
    with Session(connection.engine) as db:
        if not db.query(User).filter_by(email=email).first():
            db.add(User(email=email, name="Administrator", password_hash=hash_password(password), role="admin"))
            db.commit()
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
