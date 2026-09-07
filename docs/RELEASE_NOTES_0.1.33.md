# lai-gateway v0.1.33 Release Notes

v0.1.33 turns the Harness v0.4.6 run-event endpoint into visible Gateway UI progress. The release stays intentionally narrow: it adds metadata-only run timeline display and polling without introducing write-capable runs, browser automation, MCP tool execution, downloads, or persistent browser token storage.

## Added
- Gateway UI "Run timeline" panel backed by `GET /v1/harness/runs/{control_run_id}/events`.
- `Get selected events` button for reading the sanitized event timeline of the selected control run.
- Run polling now refreshes both the selected run status and its event timeline.

## Security
- Timeline rendering uses `textContent` only and continues to rely on the Gateway API sanitizer for event payloads.
- No Harness control token, Gateway token, pair token, Telegram token, task text, stdout, stderr, turns, or transcripts are stored in browser storage or rendered through HTML injection.
- The UI remains read-only for run control: write-capable Harness modes are still blocked at the Gateway boundary.

## Validation
- UI asset tests cover the new timeline elements and event polling route.
- `node --check` validates the static JavaScript.
- `make check` and the Gateway/Harness stack gate must pass before publication.
