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

def test_opportunity_discovery_and_saved_records(client):
    token = register(client)["access_token"]
    search = client.get(f"{API}/opportunities",
        headers=auth(token),
        params={"q": "registered nurse"},
    )
    assert search.status_code == 200
    assert len(search.json()) >= 1
    item = search.json()[0]
    saved = client.post(f"{API}/opportunities/save",
        headers=auth(token),
        json={
            "title": item["title"],
            "organization": item["organization"],
            "url": item["url"],
            "details": item["details"],
        },
    )
    assert saved.status_code == 200
    assert client.get(f"{API}/opportunities/saved", headers=auth(token)).json()
    identifier = saved.json()["id"]
    change = {"application_status": "applied"}
    other = register(client, email="other@example.com")["access_token"]
    assert client.patch(f"{API}/opportunities/saved/{identifier}", headers=auth(other), json=change).status_code == 404
    assert client.patch(f"{API}/opportunities/saved/{identifier}", headers=auth(token), json=change).json()[
        "application_status"
    ] == "applied"
