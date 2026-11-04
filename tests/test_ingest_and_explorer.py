from __future__ import annotations


def test_ingest_html_then_explore(client, auth_headers, ingest_file, sample_dir):
    j = ingest_file(sample_dir / "sample.html")
    doc_id = j["document_id"]

    # /documents
    r = client.get("/documents", headers=auth_headers)
    assert r.status_code == 200
    docs = r.json()["documents"]
    assert any(d["document_id"] == doc_id for d in docs)

    # /documents/{doc_id}
    r = client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert r.status_code == 200
    detail = r.json()
    assert detail["id"] == doc_id or detail.get("document_id") == doc_id
    # you may return either shape; this makes test tolerant:
    assert detail.get("filename") == "sample.html"

    # /documents/{doc_id}/chunks
    r = client.get(f"/documents/{doc_id}/chunks?limit=50&offset=0", headers=auth_headers)
    assert r.status_code == 200
    out = r.json()
    chunks = out.get("chunks") or out.get("items") or []
    assert len(chunks) >= 1


def test_ingest_xlsx_search_by_known_term(client, auth_headers, ingest_file, sample_dir):
    j = ingest_file(sample_dir / "sample.xlsx")
    doc_id = j["document_id"]

    # Keyword search should hit known content like "Alice"
    r = client.get(f"/search?q=Alice&doc_id={doc_id}", headers=auth_headers)
    assert r.status_code == 200
    out = r.json()
    assert out["count"] >= 1
    assert out["results"][0]["document_id"] == doc_id


def test_ingest_eml_search_by_known_term(client, auth_headers, ingest_file, sample_dir):
    j = ingest_file(sample_dir / "sample.eml")
    doc_id = j["document_id"]

    # EML contains "sender@example.com" in your preview
    r = client.get(f"/search?q=sender@example.com&doc_id={doc_id}", headers=auth_headers)
    assert r.status_code == 200
    out = r.json()
    assert out["count"] >= 1
    assert out["results"][0]["document_id"] == doc_id
