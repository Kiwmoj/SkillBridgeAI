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

def test_onet_import_search_alternate_title_comparison_and_repeat(client, tmp_path):
    archive, occupations = make_onet_archive(tmp_path)
    token = admin_token(client)
    with archive.open("rb") as stream:
        response = client.post(f"{API}/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    assert response.status_code == 200
    assert response.json()["occupations"] == len(occupations)

    nurse = client.get(f"{API}/occupations/search",
        params={"q": "Nurse"},
    )
    assert nurse.status_code == 200
    assert nurse.json()
    assert nurse.json()[0]["title"] == "Registered Nurses"

    engineer = client.get(f"{API}/occupations/search",
        params={"q": "Structural Engineer"},
    )
    assert engineer.status_code == 200
    assert engineer.json()[0]["title"] == "Civil Engineers"

    nurse_record = client.get(f"{API}/occupations/search",
        params={"q": "Registered Nurses"},
    ).json()[0]
    engineer_record = client.get(f"{API}/occupations/search",
        params={"q": "Civil Engineers"},
    ).json()[0]
    comparison = client.post(f"{API}/occupations/compare",
        json={"occupation_ids": [nurse_record["id"], engineer_record["id"]]},
    )
    assert comparison.status_code == 200
    assert len(comparison.json()["occupations"]) == 2
    assert comparison.json()["source"] == "Official O*NET descriptors"

    detail = client.get(f"{API}/occupations/{nurse_record['id']}")
    assert detail.status_code == 200
    assert detail.json()["related_occupations"]

    with archive.open("rb") as stream:
        repeated = client.post(f"{API}/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    assert repeated.status_code == 200
    assert repeated.json()["occupations"] == len(occupations)
    assert repeated.json()["alternate_titles"] == response.json()["alternate_titles"]
    again_detail = client.get(f"{API}/occupations/{nurse_record['id']}").json()
    assert len(again_detail["descriptors"]) == len(detail.json()["descriptors"])


def test_ten_industries_are_searchable(client, tmp_path):
    archive, occupations = make_onet_archive(tmp_path)
    token = admin_token(client)
    with archive.open("rb") as stream:
        response = client.post(f"{API}/admin/onet/import",
            headers=auth(token),
            params={"version": "29.0"},
            files={"file": ("onet.zip", stream, "application/zip")},
        )
    assert response.status_code == 200
    for code, title, description, industry in occupations:
        search = client.get(f"{API}/occupations/search", params={"q": title})
        assert search.status_code == 200
        assert any(item["title"] == title for item in search.json())


def test_onet_rejects_unreadable_replacement_without_losing_current_release(client, tmp_path):
    archive, _ = make_onet_archive(tmp_path)
    token = auth(admin_token(client))
    with archive.open("rb") as stream:
        assert client.post(f"{API}/admin/onet/import?version=29.0", headers=token,
                           files={"file": ("onet.zip", stream)}).is_success
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as bundle:
        bundle.writestr("db_31_0_csv/Read Me.txt", "O*NET 31.0 Database")
        bundle.writestr("db_31_0_csv/occupation_data.csv",
                       "O*NET-SOC Code,Title,Description\n29-1141.00,Changed title,Changed description")
        bundle.writestr("db_31_0_csv/essential_skills.csv",
                       "O*NET-SOC Code,Element Name,Scale ID,Data Value\n29-1141.00,Active Listening,IM,invalid")
    result = client.post(f"{API}/admin/onet/import", headers=token, files={"file": ("invalid.zip", bad.getvalue())})
    assert result.status_code == 400
    assert client.get(f"{API}/health").json()["onet_version"] == "29.0"
    assert client.get(f"{API}/occupations/search", params={"q": "29-1141.00"}).json()[0]["title"] == "Registered Nurses"


def test_load_onet_command_activates_release_without_admin_login(client, tmp_path, monkeypatch, capsys):
    import apps.backend.cli.load_onet as loader

    archive, occupations = make_onet_archive(tmp_path)
    monkeypatch.setattr(loader, "SessionLocal", lambda: Session(connection.engine))
    monkeypatch.setattr("sys.argv", ["load_onet", str(archive), "--version", "29.0"])
    loader.main()
    assert f"{len(occupations)} occupations" in capsys.readouterr().out
    assert client.get(f"{API}/health").json()["onet_version"] == "29.0"
    assert client.get(f"{API}/occupations/search", params={"q": "Nurse"}).json()[0]["title"] == "Registered Nurses"

    monkeypatch.setattr("sys.argv", ["load_onet", str(tmp_path / "missing.zip")])
    with pytest.raises(SystemExit):
        loader.main()
    assert client.get(f"{API}/health").json()["onet_version"] == "29.0"
