from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from meetingai_shared.config import WORKER_INTERNAL_TOKEN, WORKER_REQUEST_TIMEOUT


@dataclass(slots=True)
class WorkerServiceError(RuntimeError):
    message: str
    status_code: int = 500
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class WorkerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = max(int(WORKER_REQUEST_TIMEOUT), 1)

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = dict(extra or {})
        if WORKER_INTERNAL_TOKEN:
            headers["X-Worker-Token"] = WORKER_INTERNAL_TOKEN
        return headers

    def _decode_error(self, response: requests.Response) -> WorkerServiceError:
        details: dict[str, Any] | None = None
        message = response.text.strip() or f"Worker request failed with {response.status_code}."
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            details = payload
            message = str(payload.get("error") or payload.get("message") or message)
        return WorkerServiceError(message=message, status_code=response.status_code, details=details)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> Any:
        try:
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                params=params,
                json=payload,
                headers=self._headers(headers),
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            raise WorkerServiceError(
                message=f"Worker request failed: {exc}",
                status_code=503,
            ) from exc
        if response.status_code >= 400:
            raise self._decode_error(response)
        if not response.content:
            return None
        return response.json()

    def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        data: bytes,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> Any:
        try:
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                params=params,
                data=data,
                headers=self._headers(headers),
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            raise WorkerServiceError(
                message=f"Worker request failed: {exc}",
                status_code=503,
            ) from exc
        if response.status_code >= 400:
            raise self._decode_error(response)
        if not response.content:
            return None
        return response.json()
