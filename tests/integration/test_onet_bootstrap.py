from dataclasses import replace

from apps.backend.core import config
from apps.backend.services.careers import bootstrap
from tests.fixtures.api import API
from tests.fixtures.onet import make_onet_archive


def test_auto_import_loads_empty_database_once_and_honours_skips(client, tmp_path, monkeypatch):
    archive, occupations = make_onet_archive(tmp_path)
    monkeypatch.setattr(config, "settings", replace(
        config.settings, onet_auto_import=True, onet_archive_url=archive.as_uri(),
        onet_skip_files=frozenset({"tasks"}),
    ))
    assert client.get(f"{API}/health").json()["onet_version"] is None

    result = bootstrap.run_import()
    assert result is not None and result["occupations"] == len(occupations)
    assert "Tasks.txt" not in result["files"] and "Skills.txt" in result["files"]
    assert client.get(f"{API}/health").json()["onet_version"] == "user-supplied"
    assert client.get(f"{API}/occupations/search", params={"q": "Nurse"}).json()[0]["title"] == "Registered Nurses"

    assert bootstrap.run_import() is None


def test_auto_import_is_off_by_default(client):
    assert config.settings.onet_auto_import is False
    assert bootstrap.start_background_import() is False
