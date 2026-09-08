# TODO.md — Milestones

Each milestone ends with: `pytest` green, app starts, **then a code review** before moving on.
Agents: read AGENTS.md first. Do not start the next milestone before the CR of the previous
one is merged.

## M1 — Backend skeleton + blocks API
- [x] `backend/db.py`: connection helper (WAL mode), schema init from AGENTS.md, all SQL here
- [x] `backend/models.py`: Pydantic models with 15-min alignment + `end > start` validation
- [x] `backend/routes/blocks.py`: POST/GET(range)/PATCH/DELETE for blocks
- [x] `backend/main.py`: FastAPI app, include router, serve `backend/static/` at `/`
- [x] API key auth: single FastAPI dependency on the whole `/api` router (`secrets.compare_digest`, 401 on missing/wrong key, key never logged)
- [x] `requirements.txt`, minimal `README.md` (how to run)
- [x] `tests/test_blocks.py`: happy + error path per route (404, 422 on bad alignment, 422 on end<=start, 401 without/wrong key)

**Accept:** create a block via curl with the key, fetch it back, patch it, delete it; requests without the key get 401. `pytest` passes.

## M2 — Weeks + templates API
- [x] `backend/routes/weeks.py`: GET `/api/weeks/{iso_year}/{iso_week}` (blocks *overlapping* the week)
- [x] `backend/routes/templates.py`: template CRUD + apply-to-week with overlap skipping
- [x] `tests/test_weeks.py`, `tests/test_templates.py` (incl. apply skips occupied slots, ISO week boundary cases)

**Accept:** applying a template to an empty week creates its blocks; applying to a busy week
skips occupied slots. `pytest` passes.

## M3 — Frontend: grid + week navigation (read-only)
- [x] `index.html`, `style.css`: 7-day grid, 15-min rows, time labels, week header
- [x] `api.js`: all fetch calls, `X-API-Key` from `localStorage`, prompt-and-retry on 401
- [x] `calendar.js`: pure `render(state)` drawing blocks for the current week
- [x] `app.js`: state object, prev/next/today navigation, date picker
- [x] Blocks render with label + color, correct vertical position/height

**Accept:** navigate weeks in the browser, blocks from the API visible at correct positions.

## M4 — Frontend: interactions
- [x] `interact.js`: click empty grid → inline create form (label, color palette, default 1h)
- [x] Drag block body → move (15-min snap, can cross days)
- [x] Drag bottom edge → resize (15-min snap, min 15 min)
- [x] Click block → popover: edit label/color, delete
- [x] Every mutation re-fetches/re-renders; no `innerHTML` with user data

**Accept:** full CRUD works in the browser against the real API.

## M4.5 — To-do column, duration display, mobile
- [x] `GET /api/blocks/todo`: unscheduled blocks (`source="todo"`, keeps slot + duration)
- [x] To-do column in the UI: create-as-todo from the grid editor, tap card to edit/delete,
      drag card onto the grid to schedule, drop block on the column (or "To-do" button) to unschedule
- [x] To-do blocks excluded from week/range queries; scheduling/unparking preserves duration
- [x] Block duration shown in the UI (e.g. "2h 30m"), correct across midnight, also on to-do cards
- [x] Mobile: grid scrolls horizontally with min day width, fixed-size to-do column,
      editor clamped to the viewport, no body-level overflow on phones

**Accept:** park a block in To-do, drag it onto a day later with its duration intact;
all interactions usable on a phone-sized viewport. `pytest` passes.
**Accept:** park a block in To-do, drag it onto a day later; all interactions usable
on a phone-sized viewport. `pytest` passes.

## M5 — Templates UI
- [ ] "Save current week as template" flow (name + blocks)
- [ ] Template list, apply-to-current-week button (shows what was skipped)
- [ ] Template delete

**Accept:** save a week as template, apply it to a future week via UI.

## M6 — Polish + ops
- [ ] Security pass: auth on every `/api` route, input validation audit (label length, color hex, time alignment), no secrets in repo, key never logged
- [ ] README: full API reference, env vars, systemd unit + cloudflared tunnel setup
- [ ] Manual pass: all interactions, week nav, templates, API from curl
- [ ] Final full `pytest` run + code review

**Accept:** one command starts the app; README is enough for a stranger to run it.
