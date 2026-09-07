# TODO.md — Milestones

Each milestone ends with: `pytest` green, app starts, **then a code review** before moving on.
Agents: read AGENTS.md first. Do not start the next milestone before the CR of the previous
one is merged.

## M1 — Backend skeleton + blocks API
- [ ] `backend/db.py`: connection helper (WAL mode), schema init from AGENTS.md, all SQL here
- [ ] `backend/models.py`: Pydantic models with 15-min alignment + `end > start` validation
- [ ] `backend/routes/blocks.py`: POST/GET(range)/PATCH/DELETE for blocks
- [ ] `backend/main.py`: FastAPI app, include router, serve `backend/static/` at `/`
- [ ] API key auth: single FastAPI dependency on the whole `/api` router (`secrets.compare_digest`, 401 on missing/wrong key, key never logged)
- [ ] `requirements.txt`, minimal `README.md` (how to run)
- [ ] `tests/test_blocks.py`: happy + error path per route (404, 422 on bad alignment, 422 on end<=start, 401 without/wrong key)

**Accept:** create a block via curl with the key, fetch it back, patch it, delete it; requests without the key get 401. `pytest` passes.

## M2 — Weeks + templates API
- [ ] `backend/routes/weeks.py`: GET `/api/weeks/{iso_year}/{iso_week}` (blocks *overlapping* the week)
- [ ] `backend/routes/templates.py`: template CRUD + apply-to-week with overlap skipping
- [ ] `tests/test_weeks.py`, `tests/test_templates.py` (incl. apply skips occupied slots, ISO week boundary cases)

**Accept:** applying a template to an empty week creates its blocks; applying to a busy week
skips occupied slots. `pytest` passes.

## M3 — Frontend: grid + week navigation (read-only)
- [ ] `index.html`, `style.css`: 7-day grid, 15-min rows, time labels, week header
- [ ] `api.js`: all fetch calls, `X-API-Key` from `localStorage`, prompt-and-retry on 401
- [ ] `calendar.js`: pure `render(state)` drawing blocks for the current week
- [ ] `app.js`: state object, prev/next/today navigation, date picker
- [ ] Blocks render with label + color, correct vertical position/height

**Accept:** navigate weeks in the browser, blocks from the API visible at correct positions.

## M4 — Frontend: interactions
- [ ] `interact.js`: click empty grid → inline create form (label, color palette, default 1h)
- [ ] Drag block body → move (15-min snap, can cross days)
- [ ] Drag bottom edge → resize (15-min snap, min 15 min)
- [ ] Click block → popover: edit label/color, delete
- [ ] Every mutation re-fetches/re-renders; no `innerHTML` with user data

**Accept:** full CRUD works in the browser against the real API.

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
