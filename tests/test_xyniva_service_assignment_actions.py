import pytest
from pydantic import ValidationError

from xynassist_service.xyniva.structured_output import (
    XynivaStructuredOutput,
)


def test_xyniva_accepts_service_assignment_proposal():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "action",
            "action": {
                "name": "service_assignment.create",
                "arguments": {
                    "event_id": 10,
                    "group_id": 20,
                    "church_membership_id": 30,
                    "service_role": "Greeter",
                },
            },
            "prompt": "Assign this member as Greeter?",
        }
    )

    assert output.action.name == "service_assignment.create"
    assert output.action.arguments == {
        "event_id": 10,
        "group_id": 20,
        "church_membership_id": 30,
        "service_role": "Greeter",
    }


def test_xyniva_rejects_invalid_service_assignment_arguments():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "service_assignment.create",
                    "arguments": {
                        "event_id": 10,
                        "group_id": 20,
                        "church_membership_id": 0,
                        "service_role": "Greeter",
                    },
                },
                "prompt": "Assign this member?",
            }
        )


def test_xyniva_rejects_extra_service_assignment_arguments():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "service_assignment.create",
                    "arguments": {
                        "event_id": 10,
                        "group_id": 20,
                        "church_membership_id": 30,
                        "service_role": "Greeter",
                        "church_id": 999,
                    },
                },
                "prompt": "Assign this member?",
            }
        )


def test_xyniva_accepts_service_assignment_confirmation_signal():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "confirmation",
            "confirmation": {
                "action_name": "service_assignment.create",
            },
        }
    )

    assert (
        output.confirmation.action_name
        == "service_assignment.create"
    )


def test_xyniva_accepts_service_assignment_status_update():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "action",
            "action": {
                "name": "service_assignment.update_status",
                "arguments": {
                    "event_id": 10,
                    "assignment_id": 40,
                    "status": "cancelled",
                },
            },
            "prompt": "Cancel this service assignment?",
        }
    )

    assert output.action.name == "service_assignment.update_status"
    assert output.action.arguments == {
        "event_id": 10,
        "assignment_id": 40,
        "status": "cancelled",
    }


def test_xyniva_rejects_invalid_service_assignment_status_update():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "service_assignment.update_status",
                    "arguments": {
                        "event_id": 10,
                        "assignment_id": 40,
                        "status": "resurrected",
                    },
                },
                "prompt": "Change this assignment?",
            }
        )


def test_xyniva_rejects_church_id_in_status_update():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "service_assignment.update_status",
                    "arguments": {
                        "event_id": 10,
                        "assignment_id": 40,
                        "status": "cancelled",
                        "church_id": 999,
                    },
                },
                "prompt": "Cancel this assignment?",
            }
        )


def test_xyniva_accepts_service_assignment_status_confirmation():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "confirmation",
            "confirmation": {
                "action_name": "service_assignment.update_status",
            },
        }
    )

    assert (
        output.confirmation.action_name
        == "service_assignment.update_status"
    )


def test_xyniva_rejects_assigned_as_status_update_target():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "service_assignment.update_status",
                    "arguments": {
                        "event_id": 10,
                        "assignment_id": 40,
                        "status": "assigned",
                    },
                },
                "prompt": "Set this assignment to assigned?",
            }
        )
