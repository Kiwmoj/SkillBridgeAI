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
