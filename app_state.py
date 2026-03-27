from __future__ import annotations

import threading

from meetingai_api.clients.note_client import NoteWorkerClient
from meetingai_api.clients.transcription_client import MobileRecordingServiceClient, RecordingServiceClient
from meetingai_shared.repositories.meeting_store import MeetingStore
from meetingai_api.services.mobile_auth_service import MobileAuthService


store = MeetingStore()
recording_service = RecordingServiceClient()
mobile_auth_service = MobileAuthService()
mobile_recording_service = MobileRecordingServiceClient()
note_worker = NoteWorkerClient()

_analyze_lock = threading.Lock()
_analyzing_meeting_ids: set[int] = set()


def try_begin_meeting_analysis(meeting_id: int) -> bool:
    with _analyze_lock:
        if meeting_id in _analyzing_meeting_ids:
            return False
        _analyzing_meeting_ids.add(meeting_id)
        return True


def end_meeting_analysis(meeting_id: int) -> None:
    with _analyze_lock:
        _analyzing_meeting_ids.discard(meeting_id)
