from __future__ import annotations

from typing import Any

from meetingai_api.clients.worker_client import WorkerClient
from meetingai_shared.config import TRANSCRIPTION_WORKER_BASE_URL


class RecordingServiceClient(WorkerClient):
    def __init__(self) -> None:
        super().__init__(TRANSCRIPTION_WORKER_BASE_URL)

    def get_state(self, owner_username: str | None = None) -> dict[str, Any]:
        return self._request_json("GET", "/internal/recording/state", params={"owner": owner_username})

    def start(self, owner_username: str | None = None, title: str | None = None) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/internal/recording/start",
            payload={"owner_username": owner_username, "title": title},
        )

    def stop(self, owner_username: str | None = None) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/internal/recording/stop",
            payload={"owner_username": owner_username},
            timeout=120,
        )

    def list_input_devices(self) -> list[dict[str, Any]]:
        payload = self._request_json("GET", "/internal/recording/input-devices")
        return list(payload.get("items") or [])

    def set_input_device(self, preference: str | int | None) -> dict[str, Any] | None:
        payload = self._request_json(
            "POST",
            "/internal/recording/device",
            payload={"preference": preference},
        )
        return payload.get("selected")


class MobileRecordingServiceClient(WorkerClient):
    def __init__(self) -> None:
        super().__init__(TRANSCRIPTION_WORKER_BASE_URL)

    def start_session(
        self,
        owner_username: str | None,
        *,
        title: str | None = None,
        sample_rate: int = 16000,
        chunk_ms: int = 200,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/internal/mobile/sessions",
            payload={
                "owner_username": owner_username,
                "title": title,
                "sample_rate": sample_rate,
                "chunk_ms": chunk_ms,
            },
        )

    def append_chunk(
        self,
        session_id: str,
        owner_username: str | None,
        chunk: bytes,
        *,
        chunk_seq: int | None = None,
    ) -> dict[str, Any]:
        return self._request_bytes(
            "POST",
            f"/internal/mobile/sessions/{session_id}/chunks",
            data=chunk,
            params={"owner": owner_username},
            headers={
                "Content-Type": "application/octet-stream",
                **({"X-Chunk-Seq": str(chunk_seq)} if chunk_seq is not None else {}),
            },
            timeout=120,
        )

    def stop_session(self, session_id: str, owner_username: str | None) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/internal/mobile/sessions/{session_id}/stop",
            payload={"owner_username": owner_username},
            timeout=120,
        )

    def get_session_state(self, session_id: str, owner_username: str | None) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/internal/mobile/sessions/{session_id}",
            params={"owner": owner_username},
        )

    def retry_final_transcription(self, meeting_id: int, owner_username: str | None) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/internal/mobile/meetings/{meeting_id}/retry-final-transcript",
            payload={"owner_username": owner_username},
            timeout=120,
        )

    def report_client_issue(
        self,
        session_id: str,
        owner_username: str | None,
        *,
        reason: str,
        detail: str | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/internal/mobile/sessions/{session_id}/diagnostics",
            payload={
                "owner_username": owner_username,
                "reason": reason,
                "detail": detail,
            },
        )

    def list_sessions(self, owner_username: str | None) -> list[dict[str, Any]]:
        payload = self._request_json("GET", "/internal/mobile/sessions", params={"owner": owner_username})
        return list(payload.get("items") or [])
