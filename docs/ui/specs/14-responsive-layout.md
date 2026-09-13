# 14 — Responsive layout

Status: spec only. No implementation.

## Goal

Keep the Workbench usable on desktop and phone without exposing additional authority on mobile/private access.

## Desktop layout

Desktop may use three regions:

- left sidebar for projects/runs;
- center chat and composer;
- right review panel when relevant.

Debug stays collapsed below or in a secondary drawer.

## Narrow layout

On narrow screens:

- project selector moves to the header or drawer;
- chat remains primary;
- review becomes a tab/section below the chat;
- Debug remains collapsed;
- buttons stack vertically;
- no horizontal scrolling is required.

## Mobile authority rule

Responsive layout does not change backend policy. A phone-sized local browser on loopback and a private/mobile remote session are different security contexts. The UI must not unlock work/promotion because the screen is small.

## Acceptance

- First viewport on phone shows project, mode, composer, and primary action.
- Review remains reachable after a work proposal.
- Debug does not dominate mobile layout.
- Remote/private access keeps current restrictions.
