(function () {
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      window.location.reload();
    }
  });

  const initialStateNode = document.getElementById("dashboard-state");
  const stateBadge = document.getElementById("recording-status");
  const stateMeta = document.getElementById("recording-meta");
  const stateMode = document.getElementById("state-mode");
  const statePending = document.getElementById("state-pending");
  const stateVad = document.getElementById("state-vad");
  const stateSegments = document.getElementById("state-segments");
  const recordingDevice = document.getElementById("recording-device");
  const preferredDevice = document.getElementById("preferred-device");
  const segmentCount = document.getElementById("segment-count");
  const currentText = document.getElementById("current-text");
  const liveSegments = document.getElementById("live-segments");
  const meetingTitle = document.getElementById("meeting-title");
  const sessionName = document.getElementById("session-name");
  const startButton = document.getElementById("start-button");
  const stopButton = document.getElementById("stop-button");

  let previousState = null;
  if (initialStateNode) {
    try {
      previousState = JSON.parse(initialStateNode.textContent || "null");
    } catch (error) {
      console.error("Failed to parse initial dashboard state.", error);
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function updateButtons(state) {
    const isRecording = Boolean(state.is_recording);
    startButton.disabled = isRecording;
    stopButton.disabled = !isRecording;
  }

  function updateStatus(state) {
    stateBadge.textContent = state.status;
    stateBadge.className = `status-pill status-${state.status}`;

    if (state.error) {
      stateMeta.textContent = `Error: ${state.error}`;
    } else if ((state.pending_refinements || 0) > 0 && !state.is_recording) {
      stateMeta.textContent = `Refining ${state.pending_refinements} segment(s) with ${state.final_model_name || "final model"}.`;
    } else if (state.is_recording && state.started_at) {
      stateMeta.textContent = `Started: ${state.started_at}`;
    } else if (state.stopped_at) {
      stateMeta.textContent = `Stopped: ${state.stopped_at}`;
    } else {
      stateMeta.textContent = "Ready for a new session.";
    }

    if (stateMode) {
      stateMode.textContent = state.is_recording ? "recording" : (state.status || "idle");
    }

    if (statePending) {
      statePending.textContent = String(state.pending_refinements || 0);
    }

    if (stateVad) {
      stateVad.textContent = state.vad_backend || "pending";
    }

    if (recordingDevice) {
      recordingDevice.textContent = state.input_device_name
        ? `Active mic: ${state.input_device_name}`
        : "Active mic: not connected yet.";
    }

    if (preferredDevice) {
      preferredDevice.textContent = state.preferred_input_device_name
        ? `Preferred mic: ${state.preferred_input_device_name}`
        : "Preferred mic: automatic selection.";
    }
  }

  function updateLiveContent(state) {
    segmentCount.textContent = String(state.segment_count || 0);
    if (stateSegments) {
      stateSegments.textContent = String(state.segment_count || 0);
    }
    if (meetingTitle) {
      meetingTitle.textContent = state.meeting_title || "Not set";
    }
    if (sessionName) {
      sessionName.textContent = state.session_name || "pending";
    }
    currentText.textContent = state.current_text || "No transcript produced yet.";

    if (!Array.isArray(state.segments) || state.segments.length === 0) {
      liveSegments.innerHTML = '<li class="empty-state">No live output yet.</li>';
      return;
    }

    liveSegments.innerHTML = state.segments
      .map(
        (segment) => `
          <li>
            <span class="segment-time">
              ${escapeHtml(segment.start)} - ${escapeHtml(segment.end)}
              <span class="segment-phase segment-phase-${escapeHtml(segment.status || "final")}">${escapeHtml(segment.status || "final")}</span>
            </span>
            <span class="segment-text">${escapeHtml(segment.text)}</span>
          </li>
        `
      )
      .join("");
  }

  async function pollStatus() {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) {
        return;
      }

      const state = await response.json();
      updateButtons(state);
      updateStatus(state);
      updateLiveContent(state);

      const justFinishedCapture = previousState && previousState.is_recording && !state.is_recording;
      const justFinishedRefinement =
        previousState &&
        (previousState.pending_refinements || 0) > 0 &&
        (state.pending_refinements || 0) === 0 &&
        !state.is_recording;

      if (
        (justFinishedCapture && (state.pending_refinements || 0) === 0 && state.status !== "error") ||
        (justFinishedRefinement && state.status !== "error")
      ) {
        window.location.reload();
        return;
      }

      previousState = state;
    } catch (error) {
      console.error(error);
    }
  }

  updateButtons(previousState || { is_recording: false });
  updateStatus(previousState || { status: "idle", is_recording: false });
  updateLiveContent(previousState || { segment_count: 0, segments: [] });

  window.setInterval(pollStatus, 4000);
})();
