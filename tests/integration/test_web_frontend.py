"""The FastAPI app serves the single-page web frontend at / alongside the API."""
from tests.fixtures.api import API, auth, register


def test_root_serves_spa(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "SkillBridge AI" in res.text


def test_static_assets_served(client):
    for path in ("/app.js", "/styles.css", "/assets/tour-poster.png",
                 "/assets/skillbridge-tour.webm", "/assets/skillbridge-tour.mp4"):
        res = client.get(path)
        assert res.status_code == 200 and len(res.content) > 100


def test_api_and_legacy_routes_coexist_with_frontend(client):
    # The static mount at "/" must not shadow the API or its legacy aliases.
    assert client.get(f"{API}/health").status_code == 200
    assert client.get("/health").status_code == 200
    token = register(client)["access_token"]
    assert client.get(f"{API}/auth/me", headers=auth(token)).json()["email"] == "student@example.com"
    assert client.get("/openapi.json").status_code == 200
