---
name: rozvrh-milestone
description: Implement a milestone (M1-M6) from rozvrh TODO.md. Use when the user asks to implement, build, or work on a specific milestone or task from the TODO.
---

# Rozvrh Milestone Implementation

You are implementing a milestone from `TODO.md` in this repository.

## Before writing any code

1. Read `AGENTS.md` fully — it is the binding spec (stack, architecture, API contract, conventions).
2. Read the milestone in `TODO.md` you were asked to do. Do ONLY that milestone's tasks.
   Do not pull tasks forward from later milestones, even if they look easy.
3. Check what already exists — earlier milestones must be complete and reviewed before you start.

## Hard rules (from AGENTS.md — violations will be rejected in review)

- Python 3.12+, FastAPI, stdlib `sqlite3` only. No new dependencies without asking the user.
- No ORM, no background tasks, no websockets, no CORS middleware.
- Frontend: vanilla JS ES modules + CSS grid. No frameworks, no bundlers, no npm, no node_modules.
- All SQL lives in `backend/db.py` with `?` placeholders. Never string-interpolate values into SQL.
- All `/api` routes require the `X-API-Key` dependency. Compare with `secrets.compare_digest`.
  Never log the key.
- Validation: `end > start`, both 15-minute aligned, label ≤ 200 chars, color matches
  `^#[0-9a-fA-F]{6}$`.
- No `innerHTML` with user data in JS — use `textContent` / `createElement`.
- No try/except that swallows errors. No dead code, no commented-out code.
- Files stay small (~250 lines max); one responsibility per module.
- Comments only for *why*, never *what*.

## Workflow

1. Implement the milestone's tasks in the order listed in `TODO.md`.
2. Write tests as you go: every route needs a happy-path and an error-path pytest
   (including 401 without/wrong API key). Tests use FastAPI `TestClient`.
3. Run the full suite: `python -m pytest` — fix failures before proceeding.
4. Do not check off TODO items yourself unless the acceptance criteria are met.
5. When done: summarize what you built, how you validated it, and what to review.
   Do NOT start the next milestone — a code review happens first (see the
   `rozvrh-review` skill).

## Definition of done

Same as AGENTS.md §8: pytest passes, app starts with one command, no TODO/FIXME
left from this milestone, README updated if user-facing behavior changed.
