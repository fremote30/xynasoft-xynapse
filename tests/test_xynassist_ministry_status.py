"""Regression tests for XynAssist ministry status recovery."""

import httpx
import pytest

from api.services.xynassist_client import (
    XynAssistClient,
    XynAssistResponseError,
)


REQUEST_ID = "77777777-7777-4777-8777-777777777777"
OTHER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

QUIZ_RESULT = {
    "quiz": {
        "title": "Faith and Trust",
        "description": "Bible knowledge",
        "scripture": "Proverbs 3:5-6",
        "difficulty": "beginner",
    },
    "questions": [
        {
            "position": 1,
            "question_text": "Whom should we trust?",
            "option_a": "The Lord",
            "option_b": "Our own understanding",
            "option_c": "Wealth",
            "option_d": "Power",
            "correct_option": "A",
            "explanation": "Proverbs 3:5",
        }
    ],
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_client(response, seen):
    async def handler(request: httpx.Request):
        seen.append(request)

        return httpx.Response(
            200,
            json=response,
        )

    return XynAssistClient(
        base_url="http://xynassist.test",
        service_token="trusted-token",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.anyio
async def test_completed_bible_quiz_status_uses_trusted_get():
    seen = []
    response = {
        "request_id": REQUEST_ID,
        "skill": "bible_quiz.generate",
        "status": "completed",
        "result": QUIZ_RESULT,
        "error_code": None,
    }

    client = make_client(response, seen)

    result = await client.get_ministry_execution_status(
        external_user_id="user-7",
        request_id=REQUEST_ID,
    )

    assert result == response
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url.path == (
        "/api/v1/integrations/xynafaith/"
        f"ministry/executions/{REQUEST_ID}"
    )
    assert (
        seen[0].headers["X-XynAssist-Service-Token"]
        == "trusted-token"
    )
    assert (
        seen[0].headers["X-XynAssist-External-User-Id"]
        == "user-7"
    )


@pytest.mark.anyio
async def test_status_rejects_mismatched_request_id():
    response = {
        "request_id": OTHER_ID,
        "skill": "bible_quiz.generate",
        "status": "completed",
        "result": QUIZ_RESULT,
    }

    client = make_client(response, [])

    with pytest.raises(
        XynAssistResponseError,
        match="status ID mismatch",
    ):
        await client.get_ministry_execution_status(
            external_user_id="user-7",
            request_id=REQUEST_ID,
        )


@pytest.mark.anyio
async def test_status_rejects_invalid_state():
    response = {
        "request_id": REQUEST_ID,
        "skill": "bible_quiz.generate",
        "status": "unknown",
        "result": None,
    }

    client = make_client(response, [])

    with pytest.raises(
        XynAssistResponseError,
        match="Invalid ministry execution state",
    ):
        await client.get_ministry_execution_status(
            external_user_id="user-7",
            request_id=REQUEST_ID,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("bad_result", [None, {}, []])
async def test_completed_status_rejects_invalid_result(
    bad_result,
):
    response = {
        "request_id": REQUEST_ID,
        "skill": "bible_quiz.generate",
        "status": "completed",
        "result": bad_result,
    }

    client = make_client(response, [])

    with pytest.raises(
        XynAssistResponseError,
        match="Completed ministry result is invalid",
    ):
        await client.get_ministry_execution_status(
            external_user_id="user-7",
            request_id=REQUEST_ID,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state",
    ["in_progress", "failed", "uncertain"],
)
async def test_unfinished_status_has_no_result(state):
    response = {
        "request_id": REQUEST_ID,
        "skill": "bible_quiz.generate",
        "status": state,
        "result": None,
        "error_code": None,
    }

    client = make_client(response, [])

    result = await client.get_ministry_execution_status(
        external_user_id="user-7",
        request_id=REQUEST_ID,
    )

    assert result["status"] == state
    assert result["result"] is None


@pytest.mark.anyio
async def test_unfinished_status_rejects_exposed_result():
    response = {
        "request_id": REQUEST_ID,
        "skill": "bible_quiz.generate",
        "status": "in_progress",
        "result": QUIZ_RESULT,
    }

    client = make_client(response, [])

    with pytest.raises(
        XynAssistResponseError,
        match="Unfinished ministry execution exposed a result",
    ):
        await client.get_ministry_execution_status(
            external_user_id="user-7",
            request_id=REQUEST_ID,
        )


@pytest.mark.anyio
async def test_status_rejects_invalid_request_id_before_network():
    seen = []
    client = make_client({}, seen)

    with pytest.raises(
        XynAssistResponseError,
        match="Invalid ministry execution request ID",
    ):
        await client.get_ministry_execution_status(
            external_user_id="user-7",
            request_id="not-a-uuid",
        )

    assert seen == []
