# 05 — Debug disclosure

Status: spec only. No implementation.

## Goal

Keep technical diagnostics available without making them the normal workflow.

## Default state

Debug is collapsed on first load and after normal successful actions. It may auto-highlight but should not auto-open unless the user asks.

## Debug content

Allowed when already sanitized by backend contracts:

- run id;
- patch sha;
- event timeline;
- compact and raw sanitized telemetry;
- selected model id;
- local-chat contract summary;
- health and ops details;
- endpoint response bodies that are already safe for display.

Forbidden:

- control credentials;
- raw private filesystem paths when not contract-approved;
- raw prompts or transcripts when the sanitizer forbids them;
- shell command execution;
- MCP tool execution.

## Copy behavior

Copy buttons must label exactly what is copied:

- Copy run id;
- Copy sanitized events;
- Copy review payload;
- Copy health report.

No generic “copy all” if the panel mixes safe and sensitive-adjacent data.

## Visual treatment

Debug should look lower priority:

- collapsed details element or drawer;
- monospace only inside output areas;
- warning copy explaining it is troubleshooting information;
- no primary-colored destructive action inside Debug.

## Acceptance

- Normal user flow completes without opening Debug.
- Debug output has no control credentials or forbidden private paths.
- Debug controls cannot bypass loopback, review, hash, or capability gates.
