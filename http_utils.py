from __future__ import annotations

from flask import jsonify, request, session

from meetingai_api.clients.worker_client import WorkerServiceError
from meetingai_api.app_state import mobile_auth_service
from meetingai_shared.repositories.meeting_store import normalize_owner_username


def parse_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_int_list(value) -> list[int]:
    if not isinstance(value, list):
        return []
    normalized: list[int] = []
    for item in value:
        parsed = parse_int(item)
        if parsed is not None:
            normalized.append(parsed)
    return normalized


def current_session_user() -> str:
    return normalize_owner_username(session.get("user"))


def current_api_user() -> str:
    auth_user = resolve_api_user()
    if auth_user:
        return auth_user
    raise PermissionError("Authentication required.")


def resolve_api_user() -> str | None:
    token = current_api_bearer_token()
    if token:
        user = mobile_auth_service.get_user(token)
        if user:
            return normalize_owner_username(user.get("username"))
    return current_session_user() or None


def current_api_bearer_token() -> str | None:
    auth_header = str(request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        return token or None
    return None


def json_error(message: str, status: int = 400):
    return jsonify({"error": message or "Request failed."}), status


def api_exception_status(exc: Exception) -> int:
    if isinstance(exc, WorkerServiceError):
        return int(exc.status_code or 500)
    if isinstance(exc, PermissionError):
        return 401
    if isinstance(exc, FileNotFoundError):
        return 404
    if isinstance(exc, ValueError):
        return 404 if "not found" in str(exc).lower() else 400
    if isinstance(exc, RuntimeError):
        return 400
    return 500
