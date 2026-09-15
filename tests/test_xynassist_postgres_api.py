"""
Real PostgreSQL integration tests for the standalone
XynAssist conversation API.

These tests run only when:

    XYNASSIST_RUN_POSTGRES_TESTS=1

They intentionally exercise the actual HTTP routes, trusted
headers, SQLAlchemy session layer, and PostgreSQL database.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

RUN_POSTGRES = (
    os.getenv("XYNASSIST_RUN_POSTGRES_TESTS")
    == "1"
)

pytestmark = pytest.mark.skipif(
    not RUN_POSTGRES,
    reason=(
        "Set XYNASSIST_RUN_POSTGRES_TESTS=1 "
        "to run PostgreSQL integration tests"
    ),
)


def test_real_postgres_conversation_contract(
    monkeypatch,
):
    service_token = "integration-test-service-token"

    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        service_token,
    )

    # Import after the environment has been prepared.
    from xynassist_service.db.database import (
        SessionLocal,
    )
    from xynassist_service.main import app
    from xynassist_service.models import (
        Conversation,
    )

    client = TestClient(app)

    user_a = (
        "integration-user-a-"
        + uuid.uuid4().hex
    )
    user_b = (
        "integration-user-b-"
        + uuid.uuid4().hex
    )

    trusted_headers_a = {
        "X-XynAssist-Service-Token":
            service_token,
        "X-XynAssist-External-User-Id":
            user_a,
    }

    trusted_headers_b = {
        "X-XynAssist-Service-Token":
            service_token,
        "X-XynAssist-External-User-Id":
            user_b,
    }

    conversation_id = None

    try:
        create_response = client.post(
            (
                "/api/v1/integrations/"
                "xynafaith/conversations"
            ),
            headers=trusted_headers_a,
            json={
                "title": "Postgres integration test",
            },
        )

        assert create_response.status_code == 201

        created = create_response.json()

        conversation_id = created["id"]

        assert created["product"] == "xynafaith"
        assert (
            created["title"]
            == "Postgres integration test"
        )
        assert created["status"] == "active"

        list_response = client.get(
            (
                "/api/v1/integrations/"
                "xynafaith/conversations"
            ),
            headers=trusted_headers_a,
        )

        assert list_response.status_code == 200

        listed = list_response.json()

        assert any(
            item["id"] == conversation_id
            for item in listed
        )

        detail_response = client.get(
            (
                "/api/v1/integrations/"
                "xynafaith/conversations/"
                f"{conversation_id}"
            ),
            headers=trusted_headers_a,
        )

        assert detail_response.status_code == 200

        detail = detail_response.json()

        assert detail["id"] == conversation_id
        assert detail["messages"] == []

        # Another product user must not be able to
        # retrieve the conversation.
        foreign_response = client.get(
            (
                "/api/v1/integrations/"
                "xynafaith/conversations/"
                f"{conversation_id}"
            ),
            headers=trusted_headers_b,
        )

        assert foreign_response.status_code == 404

        # Another product user's list must not contain it.
        foreign_list_response = client.get(
            (
                "/api/v1/integrations/"
                "xynafaith/conversations"
            ),
            headers=trusted_headers_b,
        )

        assert foreign_list_response.status_code == 200

        assert all(
            item["id"] != conversation_id
            for item
            in foreign_list_response.json()
        )

    finally:
        db = SessionLocal()

        try:
            db.execute(
                delete(Conversation).where(
                    Conversation.external_user_id.in_(
                        [
                            user_a,
                            user_b,
                        ]
                    )
                )
            )
            db.commit()
        finally:
            db.close()
