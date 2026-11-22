from apps.backend.services.ai.service import ai_service
from tests.fixtures.api import API, auth, register

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def upload(client, token, name, content, mime):
    return client.post(f"{API}/portfolio/upload", headers=auth(token), files={"file": (name, content, mime)})


def test_pdf_upload_view_and_privacy(client):
    token = register(client)["access_token"]
    other = register(client, "Other", "other@example.com")["access_token"]
    created = upload(client, token, "resume.pdf", PDF, "application/pdf")
    assert created.status_code == 200

    item = client.get(f"{API}/portfolio", headers=auth(token)).json()[0]
    assert item["kind"] == "pdf" and item["mime_type"] == "application/pdf"

    served = client.get(item["file_url"], headers=auth(token))
    assert served.status_code == 200 and served.content == PDF
    assert served.headers["content-type"] == "application/pdf"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert served.headers["content-security-policy"] == "sandbox"

    assert client.get(item["file_url"]).status_code == 401
    assert client.get(item["file_url"], headers=auth(other)).status_code == 404
    review = client.post(f"{API}/portfolio/{item['id']}/evaluate", headers=auth(token), json={"send_to_provider": True})
    assert review.status_code == 400 and "images only" in review.json()["detail"]


def test_only_real_pdfs_and_images_are_accepted(client):
    token = register(client)["access_token"]
    assert upload(client, token, "fake.pdf", b"not a pdf at all", "application/pdf").status_code == 400
    assert upload(client, token, "truncated.pdf", b"%PDF-1.4\nno end marker", "application/pdf").status_code == 400
    assert upload(client, token, "big.pdf", PDF + b"0" * (10 * 1024 * 1024), "application/pdf").status_code == 413
    assert client.get(f"{API}/portfolio", headers=auth(token)).json() == []

def test_organize_feature_link_and_delete(client, monkeypatch):
    monkeypatch.setattr(ai_service, "status", lambda: {"provider": "gemini", "configured": True, "reachable": None})
    monkeypatch.setattr(ai_service, "generate", lambda prompt: "Generated project brief")
    token = register(client)["access_token"]
    other = register(client, "Other", "other@example.com")["access_token"]
    item_id = upload(client, token, "case-study.pdf", PDF, "application/pdf").json()["id"]
    assert upload(client, other, "x.pdf", PDF, "application/pdf").status_code == 200

    mine = client.post(f"{API}/projects", headers=auth(token), json={"occupation": "Registered Nurses"}).json()["id"]
    theirs = client.post(f"{API}/projects", headers=auth(other), json={"occupation": "Registered Nurses"}).json()["id"]
    updated = client.patch(f"{API}/portfolio/{item_id}", headers=auth(token), json={
        "title": "  Capstone  ", "description": "My write-up", "tags": ["nursing", " design "], "featured": True,
        "project_id": mine})
    assert updated.status_code == 200
    body = updated.json()
    assert body["title"] == "Capstone" and body["tags"] == ["nursing", "design"] and body["featured"] is True
    assert body["project_id"] == mine
    assert client.patch(f"{API}/portfolio/{item_id}", headers=auth(token), json={"project_id": theirs}).status_code == 404

    # Deleting the project keeps the portfolio piece but unlinks it.
    assert client.delete(f"{API}/projects/{mine}", headers=auth(token)).status_code == 200
    assert client.get(f"{API}/portfolio", headers=auth(token)).json()[0]["project_id"] is None

    # Other users cannot see, edit or delete it, and unknown projects are rejected.
    assert client.patch(f"{API}/portfolio/{item_id}", headers=auth(other), json={"title": "x"}).status_code == 404
    assert client.delete(f"{API}/portfolio/{item_id}", headers=auth(other)).status_code == 404
    assert client.patch(f"{API}/portfolio/{item_id}", headers=auth(token), json={"project_id": 9999}).status_code == 404

    # Unset featured keeps other fields; delete removes the record and the stored file.
    again = client.patch(f"{API}/portfolio/{item_id}", headers=auth(token), json={"featured": False}).json()
    assert again["featured"] is False and again["title"] == "Capstone"
    assert client.delete(f"{API}/portfolio/{item_id}", headers=auth(token)).status_code == 200
    assert [i["id"] for i in client.get(f"{API}/portfolio", headers=auth(token)).json()] == []
    assert client.get(f"{API}/portfolio/{item_id}/file", headers=auth(token)).status_code == 404
