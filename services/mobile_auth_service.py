from __future__ import annotations

from datetime import datetime, timedelta
import logging
import secrets
import threading
from typing import Any


logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_TTL_HOURS = 24
_MAX_TOKENS = 10_000


class MobileAuthService:
    def __init__(self, *, token_ttl_hours: int = _DEFAULT_TOKEN_TTL_HOURS) -> None:
        self._lock = threading.RLock()
        self._tokens: dict[str, dict[str, Any]] = {}
        self._token_ttl = timedelta(hours=max(int(token_ttl_hours), 1))

    def issue_token(self, username: str, user_dn: str | None = None) -> dict[str, str]:
        normalized_username = str(username or "").strip()
        if not normalized_username:
            raise ValueError("A valid username is required.")

        token = secrets.token_urlsafe(32)
        now = datetime.now().astimezone()
        created_at = now.isoformat(timespec="seconds")
        expires_at = now + self._token_ttl
        payload = {
            "token": token,
            "username": normalized_username,
            "user_dn": str(user_dn or "").strip() or None,
            "created_at": created_at,
            "expires_at": expires_at,
        }
        with self._lock:
            self._cleanup_expired_tokens()
            self._tokens[token] = payload
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": normalized_username,
            "created_at": created_at,
        }

    def get_user(self, token: str | None) -> dict[str, Any] | None:
        normalized_token = str(token or "").strip()
        if not normalized_token:
            return None
        with self._lock:
            payload = self._tokens.get(normalized_token)
            if payload is None:
                return None
            expires_at = payload.get("expires_at")
            if isinstance(expires_at, datetime) and datetime.now().astimezone() >= expires_at:
                self._tokens.pop(normalized_token, None)
                return None
            return dict(payload)

    def revoke(self, token: str | None) -> None:
        normalized_token = str(token or "").strip()
        if not normalized_token:
            return
        with self._lock:
            self._tokens.pop(normalized_token, None)

    def _cleanup_expired_tokens(self) -> None:
        now = datetime.now().astimezone()
        expired = [
            key
            for key, payload in self._tokens.items()
            if isinstance(payload.get("expires_at"), datetime) and now >= payload["expires_at"]
        ]
        for key in expired:
            self._tokens.pop(key, None)
        if len(self._tokens) > _MAX_TOKENS:
            logger.warning("Token store exceeded %d entries, pruning oldest.", _MAX_TOKENS)
            sorted_tokens = sorted(
                self._tokens.items(),
                key=lambda item: item[1].get("expires_at", now),
            )
            for key, _ in sorted_tokens[: len(sorted_tokens) - _MAX_TOKENS]:
                self._tokens.pop(key, None)
