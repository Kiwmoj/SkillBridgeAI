from dataclasses import replace

import pytest

from apps.backend.core import config
from apps.backend.services.careers import bootstrap
from tests.fixtures.api import API, auth, register
from tests.fixtures.onet import make_onet_archive


@pytest.fixture
def token(client, tmp_path, monkeypatch):
    archive, _ = make_onet_archive(tmp_path)
    monkeypatch.setattr(config, "settings", replace(
        config.settings, onet_auto_import=True, onet_archive_url=archive.as_uri()))
    assert bootstrap.run_import() is not None
    return register(client)["access_token"]


def set_level(client, token, level):
    return client.put(f"{API}/profile/level", headers=auth(token), json={"skill_level": level})


def test_level_is_optional_changeable_and_validated(client, token):
    info = client.get(f"{API}/profile/level", headers=auth(token)).json()
    assert info["skill_level"] is None and info["effective_level"] == "beginner"
    for level in ("advanced", "intermediate", "beginner"):
        assert set_level(client, token, level).json()["skill_level"] == level
    assert set_level(client, token, "expert").status_code in (400, 422)
    assert client.get(f"{API}/profile/level", headers=auth(token)).json()["skill_level"] == "beginner"


def test_level_changes_roadmaps_projects_and_skill_gap(client, token):
    results = {}
    for level in ("beginner", "intermediate", "advanced"):
        set_level(client, token, level)
        roadmap = client.post(f"{API}/roadmaps", headers=auth(token), json={"occupation_title": "Registered Nurses"})
        project = client.post(f"{API}/projects", headers=auth(token), json={"occupation": "Registered Nurses"})
        gap = client.post(f"{API}/skill-gap", headers=auth(token),
                          json={"occupation_title": "Registered Nurses", "current_skills": []})
        assert roadmap.status_code == project.status_code == gap.status_code == 200
        results[level] = (roadmap.json(), project.json(), gap.json())

    for level, (roadmap, project, gap) in results.items():
        assert f"Level: {level.title()}" in roadmap["content"]
        assert f"Level: {level.title()}" in project["description"]
        assert gap["level"] == level
    assert len({r[0]["content"] for r in results.values()}) == 3
    assert len({tuple(m["title"] for m in r[1]["milestones"]) for r in results.values()}) == 3
    assert len(results["beginner"][2]["focus"]) <= 3 <= len(results["advanced"][2]["focus"]) or \
        len(results["advanced"][2]["focus"]) == len(results["advanced"][2]["gaps"])


def test_profile_pathways_and_recommendations_follow_level(client, token):
    set_level(client, token, "beginner")
    recommended = client.get(f"{API}/occupations/recommended", headers=auth(token))
    assert recommended.status_code == 200 and recommended.json()["level"] == "beginner"
    occupation_id = client.get(f"{API}/occupations/search", params={"q": "Nurse"}).json()[0]["id"]
    profile = client.get(f"{API}/occupations/{occupation_id}/profile", headers=auth(token)).json()
    assert {p["id"] for p in profile["pathways"]} == {
        "university", "vocational", "apprenticeship", "certification", "self_learning"}
    beginner_tips = profile["getting_started"]
    set_level(client, token, "advanced")
    advanced = client.get(f"{API}/occupations/{occupation_id}/profile", headers=auth(token)).json()
    assert advanced["level"] == "advanced" and advanced["getting_started"] != beginner_tips
