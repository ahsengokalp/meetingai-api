from __future__ import annotations

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from meetingai_api.auth.decorators import login_required
from meetingai_api.app_state import end_meeting_analysis, note_worker, recording_service, store, try_begin_meeting_analysis
from meetingai_api.http_utils import current_session_user, parse_int
from meetingai_shared.repositories.meeting_store import meeting_can_generate_note


def register_dashboard_routes(app: Flask) -> None:
    @app.get("/")
    @login_required
    def dashboard():
        current_user = current_session_user()
        state = recording_service.get_state(current_user)
        transcripts = store.list_meetings(current_user)
        try:
            input_devices = recording_service.list_input_devices()
            input_devices_error = None
        except Exception as exc:
            input_devices = []
            input_devices_error = str(exc)

        selected_meeting_id = parse_int(request.args.get("meeting"))
        selected_note_id = parse_int(request.args.get("note"))

        if not selected_meeting_id and state.get("meeting_id"):
            selected_meeting_id = int(state["meeting_id"])
        if not selected_meeting_id and transcripts:
            selected_meeting_id = int(transcripts[0]["id"])

        selected_meeting = store.get_meeting(selected_meeting_id, current_user) if selected_meeting_id else None
        notes = store.list_notes(selected_meeting_id, current_user) if selected_meeting_id else []

        if selected_note_id and not any(note["id"] == selected_note_id for note in notes):
            selected_note_id = None
        if not selected_note_id and notes:
            selected_note_id = int(notes[0]["id"])

        selected_note = store.get_note(selected_note_id, current_user) if selected_note_id else None
        selected_transcript_text = (
            selected_meeting.get("final_transcript_text")
            or selected_meeting.get("preferred_transcript_text")
            or selected_meeting.get("raw_text")
            or ""
        ) if selected_meeting else ""

        return render_template(
            "dashboard.html",
            state=state,
            current_user=current_user,
            input_devices=input_devices,
            input_devices_error=input_devices_error,
            transcripts=transcripts,
            notes=notes,
            selected_transcript_id=selected_meeting_id,
            selected_transcript_name=selected_meeting["name"] if selected_meeting else None,
            selected_transcript_title=selected_meeting["title"] if selected_meeting else "",
            selected_transcript_text=selected_transcript_text,
            selected_note_id=selected_note_id,
            selected_note=selected_note,
            transcript_has_related_note=bool(notes),
        )

    @app.post("/recording/device")
    @login_required
    def set_recording_device():
        current_user = current_session_user()
        preference = request.form.get("device")

        try:
            selected = recording_service.set_input_device(preference)
            if selected is None:
                flash("Microphone selection reset to automatic.", "success")
            elif recording_service.get_state(current_user).get("is_recording"):
                flash(f"Preferred microphone set to {selected['name']}. It will apply on the next recording.", "success")
            else:
                flash(f"Preferred microphone set to {selected['name']}.", "success")
        except Exception as exc:
            flash(str(exc), "error")

        return redirect(url_for("dashboard"))

    @app.post("/recording/start")
    @login_required
    def start_recording():
        current_user = current_session_user()
        meeting_title = (request.form.get("meeting_title") or "").strip() or None
        try:
            recording_service.start(current_user, title=meeting_title)
            flash("Recording started.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("dashboard"))

    @app.post("/recording/stop")
    @login_required
    def stop_recording():
        current_user = current_session_user()
        try:
            recording_service.stop(current_user)
            flash("Recording stopped.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("dashboard"))

    @app.post("/analyze")
    @login_required
    def analyze():
        current_user = current_session_user()
        meeting_id = parse_int(request.form.get("meeting_id"))
        title = (request.form.get("title") or "").strip() or None

        if not meeting_id:
            flash("Pick a transcript first.", "error")
            return redirect(url_for("dashboard"))

        if not try_begin_meeting_analysis(meeting_id):
            flash("An AI note is already being generated for this meeting.", "error")
            return redirect(url_for("dashboard"))

        try:
            meeting = store.get_meeting(meeting_id, current_user)
            if meeting is None:
                flash("Meeting not found.", "error")
                return redirect(url_for("dashboard"))
            if not meeting_can_generate_note(meeting):
                flash("Final transcript hazir olmadan AI note olusturulamaz.", "error")
                return redirect(url_for("dashboard", meeting=meeting_id))
            response = note_worker.analyze_meeting(
                meeting_id,
                owner_username=current_user,
                title=title,
                requested_by=current_user,
            )
            note_id = parse_int(response.get("id"))
            mail_status = str(response.get("mail_status") or "")
            mail_error = str(response.get("mail_error") or "")
            recipient_count = int(response.get("mail_recipient_count") or 0)
            if mail_status == "sent":
                flash(
                    f"Meeting note created and emailed to {recipient_count} recipient(s).",
                    "success",
                )
            elif mail_status == "failed":
                flash(
                    f"Meeting note created, but email delivery failed: {mail_error or 'Unknown SMTP error.'}",
                    "error",
                )
            else:
                flash("Meeting note created. No participant email recipients were selected.", "success")
            return redirect(url_for("dashboard", meeting=meeting_id, note=note_id))
        except Exception as exc:
            flash(str(exc), "error")
        finally:
            end_meeting_analysis(meeting_id)
        return redirect(url_for("dashboard", meeting=meeting_id))

    @app.post("/transcripts/delete")
    @login_required
    def delete_transcript():
        current_user = current_session_user()
        meeting_id = parse_int(request.form.get("meeting_id"))
        if not meeting_id:
            flash("Pick a transcript first.", "error")
            return redirect(url_for("dashboard"))

        state = recording_service.get_state(current_user)
        if state.get("is_recording") and state.get("meeting_id") == meeting_id:
            flash("Stop the active recording before deleting its files.", "error")
            return redirect(url_for("dashboard", meeting=meeting_id))

        deleted = store.delete_meeting(meeting_id, current_user)
        if deleted is None:
            flash("Transcript not found.", "error")
            return redirect(url_for("dashboard"))

        flash(
            (
                f"Deleted {deleted['meeting_name']} with {deleted['segment_count']} segments "
                f"and {deleted['note_count']} note(s)."
            ),
            "success",
        )
        return redirect(url_for("dashboard"))

    @app.get("/api/status")
    @login_required
    def api_status():
        return jsonify(recording_service.get_state(current_session_user()))
