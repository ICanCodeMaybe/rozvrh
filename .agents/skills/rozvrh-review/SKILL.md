---
name: rozvrh-review
description: Code review gate after a rozvrh milestone. Use when the user asks to review, CR, or check the work from a milestone implementation.
---

# Rozvrh Milestone Code Review

You are reviewing the work of an agent that just finished a milestone of this project.
Your job: verify it against the spec, find real problems, and be honest — do not rubber-stamp.

## Inputs

1. Read `AGENTS.md` (the binding spec) and the milestone in `TODO.md` that was implemented.
2. Read the changed/new files (the implementer's summary should list them; if not, find them).

## Review checklist

**Spec compliance**
- Only the assigned milestone's tasks were done — no scope creep into later milestones.
- API matches the contract in AGENTS.md §4 exactly (paths, methods, status codes, shapes).
- Data model matches AGENTS.md §3 (no extra columns/tables without asking the user).

**Security (internet-facing — be strict)**
- Every `/api` route is behind the API key dependency; key compared with
  `secrets.compare_digest`; key never logged, never in the repo.
- All SQL uses `?` placeholders; no string interpolation anywhere.
- Input validation on every field: `end > start`, 15-min alignment, label ≤ 200 chars,
  color `^#[0-9a-fA-F]{6}$`.
- No `innerHTML` with user data in the frontend; no secrets in static files.

**Code quality**
- No dead code, no commented-out code, no speculative abstractions.
- No try/except that swallows errors.
- Files under ~250 lines, one responsibility per module.
- Comments explain *why* only.
- Tests: every route has a happy-path AND an error-path test (incl. 401 cases).

**Verification (do these yourself, don't trust the summary)**
- Run `python -m pytest` — must pass.
- Run `python -m mypy` — must exit zero; flag any `cast`/`type: ignore` used to silence a
  real type error instead of fixing it.
- Run `pylint backend` — must rate 10.00/10; flag any inline `# pylint: disable` pragmas.
- Start the app (`uvicorn backend.main:app --port 8000`) and hit one endpoint with curl
  (with and without the API key) if the milestone touched the backend.

## Output

Write the review as a short report:
- **Verdict**: approve / approve with fixes / reject.
- **Blocking issues**: concrete, with file paths and line references.
- **Non-blocking suggestions**: clearly separated from blockers.
- **Spec deviations**: anything that differs from AGENTS.md, flagged for the user to decide.

Do not fix issues yourself unless the user asks — the review's job is to report.
