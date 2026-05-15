from __future__ import annotations


def test_health_unprotected(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"


def test_documents_requires_api_key(client):
    r = client.get("/documents")
    assert r.status_code in (401, 403)  # depending on your auth handler
