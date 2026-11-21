import io
import zipfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.core import config
from apps.backend.core.security import SECRET
from apps.backend.database import connection, make_engine
from apps.backend.database.session import get_db
from apps.backend.main import app
from apps.backend.services.ai.providers import AIProviderError
from apps.backend.services.ai.service import ai_service
from tests.conftest import migrate
from tests.fixtures.api import API, admin_token, auth, register
from tests.fixtures.onet import make_onet_archive

def test_roadmap_project_and_activity_persist(monkeypatch, client):
    token = register(client)["access_token"]
    monkeypatch.setattr(
        ai_service,
        "generate",
        lambda prompt: "Generated educational roadmap or project",
    )
    roadmap = client.post(f"{API}/roadmaps",
        headers=auth(token),
        json={
            "occupation_title": "Registered Nurses",
            "interests": "Patient care",
            "current_skills": ["Communication"],
        },
    )
    assert roadmap.status_code == 200
    assert client.get(f"{API}/roadmaps", headers=auth(token)).status_code == 200

    project = client.post(f"{API}/projects",
        headers=auth(token),
        json={
            "occupation": "Graphic Designer",
            "title": "Community poster campaign",
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]
    updated = client.patch(f"{API}/projects/{project_id}",
        headers=auth(token),
        json={"status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    activity = client.post(f"{API}/activities",
        headers=auth(token),
        json={
            "title": "Complete portfolio case study",
            "status": "in_progress",
            "notes": "Document process",
        },
    )
    assert activity.status_code == 200
    assessment = client.post(f"{API}/assessments",
        headers=auth(token),
        json={
            "occupation_title": "Graphic Designer",
            "skill_name": "Typography",
            "rating": 4.0,
        },
    )
    assert assessment.status_code == 200
    progress = client.get(f"{API}/progress", headers=auth(token))
    assert progress.status_code == 200
    assert progress.json()["saved_roadmaps"] == 1
    assert progress.json()["project_total"] == 1
