from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import mimetypes

load_dotenv()


@pytest.fixture(scope="session")
def api_key() -> str:
    k = os.getenv("API_KEY")
    if not k:
        raise RuntimeError("API_KEY is not set (check .env and `set -a; source .env; set +a`)")
    return k


@pytest.fixture(scope="session")
def client() -> TestClient:
    # Lazy import avoids blowing up pytest collection
    from api.main import app  # noqa
    return TestClient(app)


@pytest.fixture()
def auth_headers(api_key: str) -> dict:
    return {"x-api-key": api_key}


@pytest.fixture()
def ingest_file(client, auth_headers):
    """
    Helper fixture to POST a file to /ingest/file and return JSON response.
    Usage: resp = ingest_file(path_to_file)
    """
    def _ingest(path: Path):
        path = Path(path)
        if not path.exists():
            raise RuntimeError(f"File not found: {path}")

        # Guess content-type; FastAPI UploadFile can still be octet-stream
        ctype, _ = mimetypes.guess_type(str(path))
        ctype = ctype or "application/octet-stream"

        with path.open("rb") as f:
            files = {"file": (path.name, f, ctype)}
            r = client.post("/ingest/file", headers=auth_headers, files=files)

        # Make debugging nice when failures happen
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        return r.json()

    return _ingest

@pytest.fixture(scope="session")
def sample_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / "sample_files"
    if not d.exists():
        raise RuntimeError(f"sample_files not found: {d}")
    return d
