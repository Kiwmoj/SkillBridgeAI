import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from PIL import Image

from backend.database import get_db, make_engine
from backend.main import app
from backend.models import User
from backend.security import hash_password
from backend.services.ai_providers import AIProviderError
import backend.main as main_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(main_module, "_rate_windows", {})
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    def session():
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register(client, name="Student", email="student@example.com"):
    response = client.post(
        "/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "strong-password",
        },
    )
    assert response.status_code == 200
    return response.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def admin_token(client):
    from sqlalchemy.orm import Session
    db = Session(main_module.engine)
    user = db.query(User).filter_by(email="admin@example.com").first()
    if not user:
        db.add(
            User(
                email="admin@example.com",
                name="Administrator",
                password_hash=hash_password("strong-password"),
                role="admin",
            )
        )
        db.commit()
    db.close()
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "strong-password",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def make_onet_archive(tmp_path):
    occupations = [
        ("11-1011.00", "Chief Executives", "Lead organizations", "Business"),
        ("25-2011.00", "Preschool Teachers", "Teach young children", "Education"),
        ("29-1141.00", "Registered Nurses", "Care for patients", "Healthcare"),
        ("17-2051.00", "Civil Engineers", "Design infrastructure", "Engineering"),
        ("27-1024.00", "Graphic Designers", "Create visual communications", "Arts"),
        ("51-4121.00", "Welders", "Join metal components", "Trades"),
        ("19-2041.00", "Environmental Scientists", "Study environmental systems", "Science"),
        ("41-3031.00", "Securities Traders", "Trade financial instruments", "Finance"),
        ("35-1011.00", "Chefs", "Direct food preparation", "Hospitality"),
        ("45-2011.00", "Agricultural Inspectors", "Inspect agricultural operations", "Agriculture"),
    ]
    archive = tmp_path / "onet.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(
            "Database/Occupation Data.txt",
            "O*NET-SOC Code\tTitle\tDescription\n"
            + "\n".join(
                f"{code}\t{title}\t{description}"
                for code, title, description, industry in occupations
            ),
        )
        z.writestr(
            "Database/Alternate Titles.txt",
            "O*NET-SOC Code\tAlternate Title\n"
            "29-1141.00\tNurse\n"
            "17-2051.00\tStructural Engineer",
        )
        z.writestr(
            "Database/Skills.txt",
            "O*NET-SOC Code\tElement ID\tElement Name\tData Value\tScale ID\n"
            "29-1141.00\t2-A\tActive Listening\t4.5\tLV\n"
            "17-2051.00\t2-B\tMathematics\t4.2\tLV",
        )
        z.writestr(
            "Database/Tasks.txt",
            "O*NET-SOC Code\tTask ID\tTask\n"
            "29-1141.00\t1\tAssess patient needs\n"
            "17-2051.00\t2\tReview structural drawings",
        )
        z.writestr(
            "Database/Related Occupations.txt",
            "O*NET-SOC Code\tRelated O*NET-SOC Code\tRelated Title\n"
            "29-1141.00\t29-1122.00\tOccupational Therapists",
        )
    return archive, occupations


def test_registration_login_profile_and_health(client):
    registration = register(client)
    token = registration["access_token"]
    profile = client.put(
        "/profile",
        headers=auth(token),
        json={
            "education": "Community college",
            "interests": "Nursing",
            "goals": "Become a nurse",
            "location": "Seattle",
        },
    )
    assert profile.status_code == 200
    assert profile.json()["interests"] == "Nursing"
    login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "strong-password",
        },
    )
    assert login.status_code == 200
    assert client.get("/health").json()["database"] == "healthy"


def test_authentication_and_user_data_isolation(client):
    token_a = register(client, email="a@example.com")["access_token"]
    token_b = register(client, name="B", email="b@example.com")["access_token"]
    client.put(
        "/profile",
        headers=auth(token_a),
        json={"goals": "A private goal"},
    )
    profile_b = client.get("/profile", headers=auth(token_b))
    assert profile_b.status_code == 200
    assert profile_b.json().get("goals") is None
    assert client.get("/profile").status_code == 401


def test_onet_import_search_alternate_title_comparison_and_repeat(client, tmp_path):
    archive, occupations = make_onet_archive(tmp_path)
    token = admin_token(client)
    with archive.open("rb") as stream:
        response = client.post(
            "/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    assert response.status_code == 200
    assert response.json()["occupations"] == len(occupations)

    nurse = client.get(
        "/occupations/search",
        params={"q": "Nurse"},
    )
    assert nurse.status_code == 200
    assert nurse.json()
    assert nurse.json()[0]["title"] == "Registered Nurses"

    engineer = client.get(
        "/occupations/search",
        params={"q": "Structural Engineer"},
    )
    assert engineer.status_code == 200
    assert engineer.json()[0]["title"] == "Civil Engineers"

    nurse_record = client.get(
        "/occupations/search",
        params={"q": "Registered Nurses"},
    ).json()[0]
    engineer_record = client.get(
        "/occupations/search",
        params={"q": "Civil Engineers"},
    ).json()[0]
    comparison = client.post(
        "/occupations/compare",
        json={"occupation_ids": [nurse_record["id"], engineer_record["id"]]},
    )
    assert comparison.status_code == 200
    assert len(comparison.json()["occupations"]) == 2
    assert comparison.json()["source"] == "Official O*NET descriptors"

    detail = client.get(f"/occupations/{nurse_record['id']}")
    assert detail.status_code == 200
    assert detail.json()["related_occupations"]

    with archive.open("rb") as stream:
        repeated = client.post(
            "/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    assert repeated.status_code == 200
    assert repeated.json()["occupations"] == len(occupations)
    assert repeated.json()["alternate_titles"] == response.json()["alternate_titles"]
    again_detail = client.get(f"/occupations/{nurse_record['id']}").json()
    assert len(again_detail["descriptors"]) == len(detail.json()["descriptors"])


def test_ten_industries_are_searchable(client, tmp_path):
    archive, occupations = make_onet_archive(tmp_path)
    token = admin_token(client)
    with archive.open("rb") as stream:
        response = client.post(
            "/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    assert response.status_code == 200
    for code, title, description, industry in occupations:
        search = client.get("/occupations/search", params={"q": title})
        assert search.status_code == 200
        assert any(item["title"] == title for item in search.json())


def test_custom_occupation_and_skill_gap_are_marked_unverified(client):
    token = register(client)["access_token"]
    custom = client.post(
        "/custom-occupations",
        headers=auth(token),
        json={
            "title": "Drone Racing Coach",
            "industry": "Sports and entertainment",
            "description": "Coaches competitive drone racing teams",
        },
    )
    assert custom.status_code == 200
    listed = client.get("/custom-occupations", headers=auth(token))
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Drone Racing Coach"

    gap = client.post(
        "/skill-gap",
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
        client.post(
            "/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    student_token = register(client)["access_token"]
    nurse = client.get(
        "/occupations/search",
        params={"q": "Registered Nurses"},
    ).json()[0]
    result = client.post(
        "/skill-gap",
        headers=auth(student_token),
        json={
            "occupation_id": nurse["id"],
            "current_skills": ["Active Listening"],
        },
    )
    assert result.status_code == 200
    assert result.json()["source"] == "Official O*NET descriptors"
    assert result.json()["strengths"]


def test_roadmap_project_and_activity_persist(monkeypatch, client):
    token = register(client)["access_token"]
    monkeypatch.setattr(
        main_module.ai,
        "generate",
        lambda prompt: "Generated educational roadmap or project",
    )
    roadmap = client.post(
        "/roadmaps",
        headers=auth(token),
        json={
            "occupation_title": "Registered Nurses",
            "interests": "Patient care",
            "current_skills": ["Communication"],
        },
    )
    assert roadmap.status_code == 200
    assert client.get("/roadmaps", headers=auth(token)).status_code == 200

    project = client.post(
        "/projects",
        headers=auth(token),
        json={
            "occupation": "Graphic Designer",
            "title": "Community poster campaign",
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]
    updated = client.patch(
        f"/projects/{project_id}",
        headers=auth(token),
        json={"status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    activity = client.post(
        "/activities",
        headers=auth(token),
        json={
            "title": "Complete portfolio case study",
            "status": "in_progress",
            "notes": "Document process",
        },
    )
    assert activity.status_code == 200
    assessment = client.post(
        "/assessments",
        headers=auth(token),
        json={
            "occupation_title": "Graphic Designer",
            "skill_name": "Typography",
            "rating": 4.0,
        },
    )
    assert assessment.status_code == 200
    progress = client.get("/progress", headers=auth(token))
    assert progress.status_code == 200
    assert progress.json()["saved_roadmaps"] == 1
    assert progress.json()["project_total"] == 1


def test_portfolio_upload_validation_and_evaluation(monkeypatch, client):
    token = register(client)["access_token"]
    image = Image.new("RGB", (40, 40), color=(25, 70, 130))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    monkeypatch.setattr(
        main_module.ai,
        "generate_with_image",
        lambda prompt, image_bytes, mime_type: "This is an AI-generated portfolio review.",
    )
    uploaded = client.post(
        "/portfolio/upload",
        headers=auth(token),
        files={
            "file": (
                "portfolio.png",
                buffer.getvalue(),
                "image/png",
            )
        },
    )
    assert uploaded.status_code == 200
    evaluation = client.post(
        f"/portfolio/{uploaded.json()['id']}/evaluate",
        headers=auth(token),
        json={"send_to_provider": True},
    )
    assert evaluation.status_code == 200
    assert "AI-generated" in evaluation.json()["evaluation"]

    invalid = client.post(
        "/portfolio/upload",
        headers=auth(token),
        files={
            "file": (
                "notes.txt",
                b"not an image",
                "text/plain",
            )
        },
    )
    assert invalid.status_code == 400


def test_ai_outage_is_reported_without_fake_response(monkeypatch, client):
    token = register(client)["access_token"]

    def unavailable(prompt):
        raise AIProviderError("Gemini is unavailable")

    monkeypatch.setattr(main_module.ai, "generate", unavailable)
    response = client.post(
        "/ai/generate",
        headers=auth(token),
        json={
            "purpose": "Career guidance",
            "question": "What skills do nurses need?",
        },
    )
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_contribution_moderation_consent_dataset_and_retrieval(monkeypatch, client):
    student_token = register(client)["access_token"]
    consent = client.put(
        "/training-consent",
        headers=auth(student_token),
        json={
            "consent_enabled": True,
            "disclosure_version": "2026-11-21",
        },
    )
    assert consent.status_code == 200
    contribution = client.post(
        "/contributions",
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
    monkeypatch.setattr(main_module.ai, "generate", lambda prompt: prompts.append(prompt) or "General guidance.")
    question = {"purpose": "Learning recommendations", "question": "nursing study communication"}
    pending_rag = client.post("/ai/generate", headers=auth(student_token), json=question)
    assert not pending_rag.json()["sources"]
    token = admin_token(client)
    review = client.post(
        f"/admin/contributions/{contribution_id}/review",
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

    rag = client.post(
        "/ai/generate",
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

    dataset = client.post(
        "/admin/datasets/build",
        headers=auth(token),
        json={"name": "community-draft-v1"},
    )
    assert dataset.status_code == 200
    assert dataset.json()["training_performed"] is False
    assert dataset.json()["train_count"] >= 1
    records = client.get(
        f"/admin/datasets/{dataset.json()['id']}/records",
        headers=auth(token),
    )
    assert records.status_code == 200
    assert records.json()["dataset"]["name"] == "community-draft-v1"
    assert records.json()["records"]

    withdrawn = client.put(
        "/training-consent",
        headers=auth(student_token),
        json={
            "consent_enabled": False,
            "disclosure_version": "2026-11-21",
        },
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["consent_enabled"] is False
    mine = client.get("/contributions", headers=auth(student_token)).json()
    assert mine[0]["consent_to_training"] is False
    revoked = client.get(f"/admin/datasets/{dataset.json()['id']}/records", headers=auth(token))
    assert revoked.status_code == 409
    assert client.get("/admin/dashboard", headers=auth(token)).json()["dataset_records"] == 0
    assert client.put("/training-consent", headers=auth(student_token), json={"consent_enabled": True}).is_success
    assert not client.get("/contributions", headers=auth(student_token)).json()[0]["consent_to_training"]


def test_contribution_blocks_missing_global_consent_and_copyright(client):
    student_token = register(client)["access_token"]
    mismatch = client.post(
        "/contributions",
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

    unconfirmed = client.post(
        "/contributions",
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


def test_opportunity_discovery_and_saved_records(client):
    token = register(client)["access_token"]
    search = client.get(
        "/opportunities",
        headers=auth(token),
        params={"q": "registered nurse"},
    )
    assert search.status_code == 200
    assert len(search.json()) >= 1
    item = search.json()[0]
    saved = client.post(
        "/opportunities/save",
        headers=auth(token),
        json={
            "title": item["title"],
            "organization": item["organization"],
            "url": item["url"],
            "details": item["details"],
        },
    )
    assert saved.status_code == 200
    assert client.get("/opportunities/saved", headers=auth(token)).json()
    identifier = saved.json()["id"]
    change = {"application_status": "applied"}
    other = register(client, email="other@example.com")["access_token"]
    assert client.patch(f"/opportunities/saved/{identifier}", headers=auth(other), json=change).status_code == 404
    assert client.patch(f"/opportunities/saved/{identifier}", headers=auth(token), json=change).json()[
        "application_status"
    ] == "applied"


def test_password_recovery_and_account_deletion(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "student@example.com")
    account = register(client)
    assert account["role"] == "student"
    original = auth(account["access_token"])
    assert client.get("/admin/dashboard", headers=original).status_code == 403
    current = {"password": "strong-password"}
    generated = client.post("/auth/recovery-code", headers=original, json=current)
    assert generated.is_success
    reset = {"email": "student@example.com", "password": "new-example-password",
             "recovery_code": generated.json()["recovery_code"]}
    assert client.post("/auth/reset-password", json=reset).is_success
    assert client.post("/auth/reset-password", json=reset).status_code == 400
    assert client.get("/profile", headers=original).status_code == 401
    credentials = {"email": reset["email"], "password": reset["password"]}
    signed_in = client.post("/auth/login", json=credentials)
    assert signed_in.is_success
    authorized = auth(signed_in.json()["access_token"])
    assert client.post("/auth/logout", headers=authorized).is_success
    assert client.get("/profile", headers=authorized).status_code == 401
    signed_in = client.post("/auth/login", json=credentials)
    authorized = auth(signed_in.json()["access_token"])
    assert client.post("/auth/delete-account", headers=authorized, json=current).status_code == 403
    assert client.post("/auth/delete-account", headers=authorized, json={"password": reset["password"]}).is_success
    assert client.post("/auth/login", json=credentials).status_code == 401


def test_onet_rejects_unreadable_replacement_without_losing_current_release(client, tmp_path):
    archive, _ = make_onet_archive(tmp_path)
    token = auth(admin_token(client))
    with archive.open("rb") as stream:
        assert client.post("/admin/onet/import?version=29.0", headers=token,
                           files={"file": ("onet.zip", stream)}).is_success
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as bundle:
        bundle.writestr("db_31_0_csv/Read Me.txt", "O*NET 31.0 Database")
        bundle.writestr("db_31_0_csv/occupation_data.csv",
                       "O*NET-SOC Code,Title,Description\n29-1141.00,Changed title,Changed description")
        bundle.writestr("db_31_0_csv/essential_skills.csv",
                       "O*NET-SOC Code,Element Name,Scale ID,Data Value\n29-1141.00,Active Listening,IM,invalid")
    result = client.post("/admin/onet/import", headers=token, files={"file": ("invalid.zip", bad.getvalue())})
    assert result.status_code == 400
    assert client.get("/health").json()["onet_version"] == "29.0"
    assert client.get("/occupations/search", params={"q": "29-1141.00"}).json()[0]["title"] == "Registered Nurses"


def test_load_onet_command_activates_release_without_admin_login(client, tmp_path, monkeypatch, capsys):
    import backend.load_onet as loader
    from sqlalchemy.orm import sessionmaker

    archive, occupations = make_onet_archive(tmp_path)
    monkeypatch.setattr(loader, "SessionLocal", sessionmaker(bind=main_module.engine))
    monkeypatch.setattr("sys.argv", ["load_onet", str(archive), "--version", "29.0"])
    loader.main()
    assert f"{len(occupations)} occupations" in capsys.readouterr().out
    assert client.get("/health").json()["onet_version"] == "29.0"
    assert client.get("/occupations/search", params={"q": "Nurse"}).json()[0]["title"] == "Registered Nurses"

    monkeypatch.setattr("sys.argv", ["load_onet", str(tmp_path / "missing.zip")])
    with pytest.raises(SystemExit):
        loader.main()
    assert client.get("/health").json()["onet_version"] == "29.0"
