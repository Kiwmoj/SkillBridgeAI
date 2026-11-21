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

def test_custom_occupation_and_skill_gap_are_marked_unverified(client):
    token = register(client)["access_token"]
    custom = client.post(f"{API}/custom-occupations",
        headers=auth(token),
        json={
            "title": "Drone Racing Coach",
            "industry": "Sports and entertainment",
            "description": "Coaches competitive drone racing teams",
        },
    )
    assert custom.status_code == 200
    listed = client.get(f"{API}/custom-occupations", headers=auth(token))
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Drone Racing Coach"

    gap = client.post(f"{API}/skill-gap",
        headers=auth(token),
        json={
            "occupation_title": "Drone Racing Coach",
            "current_skills": ["Communication"],
        },
    )
    assert gap.status_code == 200
    assert gap.json()["source"] == "Not verified against O*NET"
    assert gap.json()["occupation"] == "Drone Racing Coach"


def test_skill_gap_uses_imported_onet_descriptors(client, tmp_path):
    archive, occupations = make_onet_archive(tmp_path)
    token = admin_token(client)
    with archive.open("rb") as stream:
        client.post(f"{API}/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    student_token = register(client)["access_token"]
    nurse = client.get(f"{API}/occupations/search",
        params={"q": "Registered Nurses"},
    ).json()[0]
    result = client.post(f"{API}/skill-gap",
        headers=auth(student_token),
        json={
            "occupation_id": nurse["id"],
            "current_skills": ["Active Listening"],
        },
    )
    assert result.status_code == 200
    assert result.json()["source"] == "Official O*NET descriptors"
    assert result.json()["strengths"]
