# 07 — Visual system

Status: spec only. No implementation.

## Goal

Make the UI clean, calm, and operationally legible. Avoid dashboard overload.

## Density

Default density should prioritize reading and decisions over controls:

- generous spacing around composer;
- compact status chips;
- hidden secondary controls;
- no large raw diagnostic panels on the primary screen.

## Color semantics

Use a restrained state vocabulary:

- neutral: idle or informational;
- blue/running: active work;
- green/ready: validated or safe to proceed;
- yellow/warn: needs attention or incomplete;
- red/danger: failure, blocked, or unsafe.

Do not rely on color alone; every state needs text.

## Typography

- System UI font for normal text.
- Monospace only for code, diff, IDs, and Debug output.
- Short labels on buttons.
- Verbose explanations go into helper text or Debug.

## Button hierarchy

At most one primary action per context:

- Send to LAI;
- Review change;
- Apply change;
- Reconnect.

Danger actions remain secondary and explicit:

- Cancel active run;
- Discard review selection.

## Empty states

Good empty states explain what to do next:

- “Choose a project and ask LAI what to inspect.”
- “No proposal to review yet.”
- “Debug is empty until a run exists.”

## Acceptance

- The first viewport is not dominated by buttons.
- Normal operation requires no horizontal scroll on mobile.
- Every status state has a text label and an accessible live region where appropriate.
