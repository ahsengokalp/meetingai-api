from __future__ import annotations

from flask import Flask, jsonify, request

from meetingai_api.app_state import (
    end_meeting_analysis,
    mobile_auth_service,
    mobile_recording_service,
    note_worker,
    recording_service,
    store,
    try_begin_meeting_analysis,
)
from meetingai_api.http_utils import (
    api_exception_status,
    current_api_bearer_token,
    current_api_user,
    json_error,
    parse_int,
    parse_int_list,
)
from meetingai_api.services.ldap_service import LdapService
from meetingai_shared.repositories.meeting_store import meeting_can_generate_note


def register_mobile_api_routes(app: Flask) -> None:
    @app.post("/api/mobile/auth/login")
    def api_mobile_login():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username") or "").strip()
        password = str(data.get("password") or "")
        if not username or not password:
            return json_error("Username and password are required.", 400)

        user = LdapService.authenticate(username, password)
        if not user:
            return json_error("Invalid credentials.", 401)
        return jsonify(mobile_auth_service.issue_token(user["username"], user.get("user_dn")))

    @app.post("/api/mobile/auth/logout")
    def api_mobile_logout():
        mobile_auth_service.revoke(current_api_bearer_token())
        return jsonify({"ok": True})

    @app.get("/api/mobile/me")
    def api_mobile_me():
        try:
            current_user = current_api_user()
            return jsonify({"username": current_user})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/sessions")
    def api_mobile_sessions():
        try:
            current_user = current_api_user()
            return jsonify({"items": mobile_recording_service.list_sessions(current_user)})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.post("/api/mobile/sessions")
    def api_mobile_start_session():
        try:
            current_user = current_api_user()
            data = request.get_json(silent=True) or {}
            state = mobile_recording_service.start_session(
                current_user,
                title=str(data.get("meeting_title") or "").strip() or None,
                sample_rate=parse_int(data.get("sample_rate")) or 16000,
                chunk_ms=parse_int(data.get("chunk_ms")) or 200,
            )
            participant_ids = parse_int_list(data.get("participant_ids"))
            if participant_ids:
                store.replace_meeting_participants(
                    int(state["meeting_id"]),
                    participant_ids,
                    owner_username=current_user,
                )
            return jsonify(state), 201
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/users/search")
    def api_mobile_search_users():
        try:
            current_api_user()
            query = str(request.args.get("q") or "").strip()
            limit = parse_int(request.args.get("limit")) or 8
            return jsonify({"items": store.search_users(query, limit=limit)})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/sessions/<session_id>")
    def api_mobile_session_status(session_id: str):
        try:
            current_user = current_api_user()
            return jsonify(mobile_recording_service.get_session_state(session_id, current_user))
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.post("/api/mobile/sessions/<session_id>/diagnostics")
    def api_mobile_session_diagnostics(session_id: str):
        try:
            current_user = current_api_user()
            payload = request.get_json(silent=True) or {}
            reason = str(payload.get("reason") or "").strip()
            detail = str(payload.get("detail") or "").strip() or None
            if not reason:
                return json_error("Diagnostic reason is required.", 400)
            state = mobile_recording_service.report_client_issue(
                session_id,
                current_user,
                reason=reason,
                detail=detail,
            )
            return jsonify({"ok": True, "state": state})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.post("/api/mobile/sessions/<session_id>/chunks")
    def api_mobile_upload_chunk(session_id: str):
        try:
            current_user = current_api_user()
            chunk = request.get_data(cache=False, as_text=False)
            if not chunk:
                return json_error("Audio chunk is empty.", 400)
            chunk_seq = parse_int(request.headers.get("X-Chunk-Seq"))
            state = mobile_recording_service.append_chunk(
                session_id,
                current_user,
                chunk,
                chunk_seq=chunk_seq,
            )
            return jsonify({"ok": True, "state": state})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.post("/api/mobile/sessions/<session_id>/stop")
    def api_mobile_stop_session(session_id: str):
        try:
            current_user = current_api_user()
            return jsonify(mobile_recording_service.stop_session(session_id, current_user))
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/meetings")
    def api_mobile_meetings():
        try:
            current_user = current_api_user()
            return jsonify({"items": store.list_meetings(current_user)})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/mail-history")
    def api_mobile_mail_history():
        try:
            current_user = current_api_user()
            limit = parse_int(request.args.get("limit")) or 25
            return jsonify({"items": store.list_mail_delivery_batches(current_user, limit=limit)})
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/meetings/<int:meeting_id>")
    def api_mobile_meeting_detail(meeting_id: int):
        try:
            current_user = current_api_user()
            meeting = store.get_meeting(meeting_id, current_user)
            if meeting is None:
                return json_error("Meeting not found.", 404)
            return jsonify(
                {
                    "meeting": meeting,
                    "notes": store.list_notes(meeting_id, current_user),
                    "participants": store.list_meeting_participants(meeting_id, current_user),
                    "mail_summary": store.get_meeting_mail_summary(meeting_id, current_user),
                    "mail_history": store.list_mail_delivery_batches(
                        current_user,
                        meeting_id=meeting_id,
                        limit=10,
                    ),
                }
            )
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.route("/api/mobile/meetings/<int:meeting_id>/delete", methods=["POST"])
    def api_mobile_delete_meeting(meeting_id: int):
        try:
            current_user = current_api_user()
            state = recording_service.get_state(current_user)
            if state.get("is_recording") and state.get("meeting_id") == meeting_id:
                return json_error("Stop the active recording before deleting its transcript.", 409)

            mobile_sessions = mobile_recording_service.list_sessions(current_user)
            for session in mobile_sessions:
                if session.get("is_recording") and int(session.get("meeting_id") or 0) == meeting_id:
                    return json_error("Stop the active mobile recording before deleting its transcript.", 409)

            deleted = store.delete_meeting(meeting_id, current_user)
            if deleted is None:
                return json_error("Meeting not found.", 404)
            return jsonify(deleted)
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.post("/api/mobile/meetings/<int:meeting_id>/analyze")
    def api_mobile_analyze_meeting(meeting_id: int):
        try:
            current_user = current_api_user()
            if not try_begin_meeting_analysis(meeting_id):
                return json_error("AI note generation is already in progress for this meeting.", 409)
            meeting = store.get_meeting(meeting_id, current_user)
            if meeting is None:
                return json_error("Meeting not found.", 404)
            if not meeting_can_generate_note(meeting):
                return json_error("Final transcript is not ready yet. Wait for large-v3 transcription to finish.", 409)
            data = request.get_json(silent=True) or {}
            title = str(data.get("title") or "").strip() or None
            response = note_worker.analyze_meeting(
                meeting_id,
                owner_username=current_user,
                title=title,
                requested_by=current_user,
            )
            return jsonify(response), 201
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))
        finally:
            end_meeting_analysis(meeting_id)

    @app.post("/api/mobile/meetings/<int:meeting_id>/retry-final-transcript")
    def api_mobile_retry_final_transcript(meeting_id: int):
        try:
            current_user = current_api_user()
            meeting = mobile_recording_service.retry_final_transcription(meeting_id, current_user)
            return jsonify(meeting), 202
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.post("/api/mobile/notes/<int:note_id>/send-mail")
    def api_mobile_resend_note_mail(note_id: int):
        try:
            current_user = current_api_user()
            result = note_worker.resend_note_mail(
                note_id,
                owner_username=current_user,
                requested_by=current_user,
            )
            return jsonify(result)
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))

    @app.get("/api/mobile/notes/<int:note_id>")
    def api_mobile_note(note_id: int):
        try:
            current_user = current_api_user()
            note = store.get_note(note_id, current_user)
            if note is None:
                return json_error("Meeting note not found.", 404)
            return jsonify(note)
        except Exception as exc:
            return json_error(str(exc), api_exception_status(exc))
