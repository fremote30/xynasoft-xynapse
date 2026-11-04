import json
import os
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials


class FirebaseAuthError(Exception):
    """Base Firebase authentication error."""


class FirebaseConfigurationError(FirebaseAuthError):
    """Firebase Admin credentials are missing or invalid."""


class FirebaseTokenError(FirebaseAuthError):
    """Firebase ID token could not be verified."""


class FirebasePhoneMissingError(FirebaseAuthError):
    """Verified Firebase identity does not contain a phone number."""


def _get_firebase_app():
    """
    Return the Firebase Admin app, initializing it once if necessary.

    Credentials are supplied through FIREBASE_SERVICE_ACCOUNT_JSON.
    The service-account JSON must never be committed to source control.
    """

    try:
        return firebase_admin.get_app()

    except ValueError:
        pass

    raw_credentials = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON"
    )

    if not raw_credentials:
        raise FirebaseConfigurationError(
            "FIREBASE_SERVICE_ACCOUNT_JSON is not configured"
        )

    try:
        service_account: dict[str, Any] = json.loads(
            raw_credentials
        )

    except json.JSONDecodeError as exc:
        raise FirebaseConfigurationError(
            "FIREBASE_SERVICE_ACCOUNT_JSON is invalid JSON"
        ) from exc

    required_fields = {
        "project_id",
        "private_key",
        "client_email",
    }

    missing = required_fields.difference(
        service_account.keys()
    )

    if missing:
        raise FirebaseConfigurationError(
            "Firebase service account is missing required fields"
        )

    try:
        credential = credentials.Certificate(
            service_account
        )

        return firebase_admin.initialize_app(
            credential
        )

    except Exception as exc:
        raise FirebaseConfigurationError(
            "Firebase Admin initialization failed"
        ) from exc


def verify_firebase_phone_token(
    id_token: str,
) -> dict[str, Any]:
    """
    Verify a Firebase Authentication ID token and require that
    Firebase has verified a phone-number identity.

    Returns:
        {
            "firebase_uid": "...",
            "phone": "+15551234567",
            "claims": {...}
        }
    """

    token = (id_token or "").strip()

    if not token:
        raise FirebaseTokenError(
            "Firebase ID token is required"
        )

    app = _get_firebase_app()

    try:
        claims = auth.verify_id_token(
            token,
            app=app,
            check_revoked=True,
        )

    except Exception as exc:
        raise FirebaseTokenError(
            "Invalid or expired Firebase ID token"
        ) from exc

    firebase_uid = claims.get("uid")

    if not firebase_uid:
        raise FirebaseTokenError(
            "Firebase token is missing a user identity"
        )

    phone = claims.get("phone_number")

    if not phone:
        raise FirebasePhoneMissingError(
            "Firebase identity does not contain a verified phone number"
        )

    phone = phone.strip()

    if not phone.startswith("+"):
        raise FirebasePhoneMissingError(
            "Firebase phone number is not in international format"
        )

    return {
        "firebase_uid": firebase_uid,
        "phone": phone,
        "claims": claims,
    }
