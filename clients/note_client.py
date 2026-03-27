from __future__ import annotations

from typing import Any

from meetingai_api.clients.worker_client import WorkerClient
from meetingai_shared.config import NOTE_ANALYZE_REQUEST_TIMEOUT, NOTE_WORKER_BASE_URL


class NoteWorkerClient(WorkerClient):
    def __init__(self) -> None:
        super().__init__(NOTE_WORKER_BASE_URL)

    def analyze_meeting(
        self,
        meeting_id: int,
        *,
        owner_username: str | None,
        title: str | None = None,
        requested_by: str | None = None,
        trigger_source: str = "analyze",
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/internal/meetings/{meeting_id}/analyze",
            payload={
                "owner_username": owner_username,
                "title": title,
                "requested_by": requested_by,
                "trigger_source": trigger_source,
            },
            timeout=NOTE_ANALYZE_REQUEST_TIMEOUT,
        )

    def resend_note_mail(
        self,
        note_id: int,
        *,
        owner_username: str | None,
        requested_by: str | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/internal/notes/{note_id}/send-mail",
            payload={
                "owner_username": owner_username,
                "requested_by": requested_by,
            },
            timeout=300,
        )
