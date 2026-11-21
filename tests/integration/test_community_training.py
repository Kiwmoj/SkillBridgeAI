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

def test_contribution_moderation_consent_dataset_and_retrieval(monkeypatch, client):
    student_token = register(client)["access_token"]
    consent = client.put(f"{API}/training-consent",
        headers=auth(student_token),
        json={
            "consent_enabled": True,
            "disclosure_version": "2026-11-21",
        },
    )
    assert consent.status_code == 200
    contribution = client.post(f"{API}/contributions",
        headers=auth(student_token),
        json={
            "title": "Verified study plan for nursing students",
            "body": "Use official nursing curricula and supervised clinical practice to build patient communication skills.",
            "category": "learning_resource",
            "source": "https://www.nursingworld.org/",
            "consent_to_training": True,
            "copyright_confirmed": True,
        },
    )
    assert contribution.status_code == 200
    assert contribution.json()["review_status"] == "pending"
    contribution_id = contribution.json()["id"]

    prompts = []
    monkeypatch.setattr(ai_service, "generate", lambda prompt: prompts.append(prompt) or "General guidance.")
    question = {"purpose": "Learning recommendations", "question": "nursing study communication"}
    pending_rag = client.post(f"{API}/ai/generate", headers=auth(student_token), json=question)
    assert not pending_rag.json()["sources"]
    token = admin_token(client)
    review = client.post(f"{API}/admin/contributions/{contribution_id}/review",
        headers=auth(token),
        json={
            "status": "approved",
            "deidentified": True,
            "quality_rating": 4.5,
            "notes": "Reviewed for educational usefulness",
        },
    )
    assert review.status_code == 200
    assert review.json()["review_status"] == "approved"

    rag = client.post(f"{API}/ai/generate",
        headers=auth(student_token),
        json={
            "purpose": "Learning recommendations",
            "question": "nursing study communication",
        },
    )
    assert rag.status_code == 200
    assert rag.json()["sources"]
    assert rag.json()["sources"][0]["source_type"] == "community"
    assert rag.json()["sources"][0]["verified"] is False
    assert "supervised clinical practice" in prompts[-1]

    dataset = client.post(f"{API}/admin/datasets/build",
        headers=auth(token),
        json={"name": "community-draft-v1"},
    )
    assert dataset.status_code == 200
    assert dataset.json()["training_performed"] is False
    assert dataset.json()["train_count"] >= 1
    records = client.get(f"{API}/admin/datasets/{dataset.json()['id']}/records",
        headers=auth(token),
    )
    assert records.status_code == 200
    assert records.json()["dataset"]["name"] == "community-draft-v1"
    assert records.json()["records"]

    withdrawn = client.put(f"{API}/training-consent",
        headers=auth(student_token),
        json={
            "consent_enabled": False,
            "disclosure_version": "2026-11-21",
        },
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["consent_enabled"] is False
    mine = client.get(f"{API}/contributions", headers=auth(student_token)).json()
    assert mine[0]["consent_to_training"] is False
    revoked = client.get(f"{API}/admin/datasets/{dataset.json()['id']}/records", headers=auth(token))
    assert revoked.status_code == 409
    assert client.get(f"{API}/admin/dashboard", headers=auth(token)).json()["dataset_records"] == 0
    assert client.put(f"{API}/training-consent", headers=auth(student_token), json={"consent_enabled": True}).is_success
    assert not client.get(f"{API}/contributions", headers=auth(student_token)).json()[0]["consent_to_training"]


def test_contribution_blocks_missing_global_consent_and_copyright(client):
    student_token = register(client)["access_token"]
    mismatch = client.post(f"{API}/contributions",
        headers=auth(student_token),
        json={
            "title": "Contribution with training permission",
            "body": "This submission should require explicit Settings consent before training permission.",
            "category": "career_research",
            "consent_to_training": True,
            "copyright_confirmed": True,
        },
    )
    assert mismatch.status_code == 400

    unconfirmed = client.post(f"{API}/contributions",
        headers=auth(student_token),
        json={
            "title": "Public educational contribution",
            "body": "This submission is for public educational review and is not being offered for training.",
            "category": "career_research",
            "consent_to_training": False,
            "copyright_confirmed": False,
        },
    )
    assert unconfirmed.status_code == 400
