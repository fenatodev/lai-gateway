const READ_ONLY_MODES = new Set(["diagnose", "plan", "release", "review", "security"]);

function pretty(payload) {
  return JSON.stringify(payload, null, 2);
}

function show(targetId, payload) {
  document.getElementById(targetId).textContent = typeof payload === "string" ? payload : pretty(payload);
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { "Accept": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (_err) {
    payload = { error: "invalid_json", body: text };
  }
  if (!response.ok) {
    throw new Error(pretty({ status: response.status, payload }));
  }
  return payload;
}

function setSessionFromPayload(payload) {
  const session = payload.session || (payload.sessions && payload.sessions[0]);
  if (session && session.session_id) {
    document.getElementById("session-id").value = session.session_id;
  }
}

function setRunFromPayload(payload) {
  const run = payload.run || (payload.runs && payload.runs[0]);
  if (run && run.control_run_id) {
    document.getElementById("run-id").value = run.control_run_id;
  }
}

async function runAction(action) {
  try {
    if (action === "refresh-status") {
      show("status-output", await requestJson("/v1/harness/status"));
    } else if (action === "refresh-readiness") {
      show("status-output", await requestJson("/v1/harness/readiness"));
    } else if (action === "list-sessions") {
      const payload = await requestJson("/v1/harness/sessions?limit=10");
      setSessionFromPayload(payload);
      show("sessions-output", payload);
    } else if (action === "create-session") {
      const payload = await requestJson("/v1/harness/sessions", { method: "POST" });
      setSessionFromPayload(payload);
      show("sessions-output", payload);
    } else if (action === "get-session") {
      const sessionId = document.getElementById("session-id").value.trim();
      if (!sessionId) throw new Error("session id is required");
      show("sessions-output", await requestJson(`/v1/harness/sessions/${encodeURIComponent(sessionId)}`));
    } else if (action === "list-runs") {
      const payload = await requestJson("/v1/harness/runs?limit=10");
      setRunFromPayload(payload);
      show("runs-output", payload);
    } else if (action === "create-run") {
      const mode = document.getElementById("run-mode").value;
      const task = document.getElementById("run-task").value.trim();
      const sessionId = document.getElementById("session-id").value.trim();
      if (!READ_ONLY_MODES.has(mode)) throw new Error("mode must be read-only");
      if (!task) throw new Error("task is required");
      const body = { mode, task };
      if (sessionId) body.session_id = sessionId;
      const payload = await requestJson("/v1/harness/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(body),
      });
      setRunFromPayload(payload);
      show("runs-output", payload);
    } else if (action === "get-run") {
      const runId = document.getElementById("run-id").value.trim();
      if (!runId) throw new Error("run id is required");
      show("runs-output", await requestJson(`/v1/harness/runs/${encodeURIComponent(runId)}`));
    }
  } catch (err) {
    const target = action.includes("session") ? "sessions-output" : action.includes("run") ? "runs-output" : "status-output";
    show(target, String(err.message || err));
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  runAction(button.dataset.action);
});

document.addEventListener("DOMContentLoaded", () => {
  runAction("refresh-readiness");
});
