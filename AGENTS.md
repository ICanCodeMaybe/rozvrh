# AGENTS.md — "Rozvrh" Weekly Calendar App

Single-user weekly calendar web app that runs on a home server (an older Arch Linux laptop),
exposed to the internet through a Cloudflare tunnel.
Read this file fully before writing any code.

## 1. Product requirements

- Displays a weekly calendar (Mon–Sun) that resembles a todo list: colored blocks placed on a time grid.
- Blocks have: label (text), color, start time, end time. "Size" = time span (resize = change duration).
- User can add, move (drag), resize, and remove blocks.
- The user can see and plan 2–3 weeks ahead (week navigation, no hard limit).
- "Base calendar" templates: predefined sets of blocks that can be applied to prefill an upcoming week.
- A basic HTTP API for fetching and modifying the calendar, so other personal projects can integrate.

## 2. Tech stack (decided — do not change without asking the user)

| Layer     | Choice                              | Why |
|-----------|-------------------------------------|-----|
| Backend   | **Python 3.12+, FastAPI, uvicorn**  | Readable, low resource usage, built-in OpenAPI docs |
| Database  | **SQLite** via the stdlib `sqlite3` module, WAL mode | Zero config, one file, fine for a single user |
| Frontend  | **Vanilla JS (ES modules) + CSS grid**, no build step, no npm | Runs on old hardware; agents must not pull in React/Vue/etc. |
| Auth      | **Mandatory API key** on all `/api` routes (env `ROZVRH_API_KEY`), constant-time compare | App is internet-facing; the key is the only auth |
| Tests     | `pytest` for backend; API tested via FastAPI `TestClient` | |
| Types     | **mypy** (strict-ish: `disallow_untyped_defs`, `warn_return_any`), config in `mypy.ini` | Catches type bugs like wrong return types before review |
| Linter    | **pylint** (10.00/10 required), config in `.pylintrc` | Catches code smells, dead code, shadowing that mypy misses |

Hard constraints:
- **No frontend frameworks, no bundlers, no node_modules.** Static files served by FastAPI.
- **No ORM.** Raw SQL in a single `db.py` with small helper functions. Keep queries in one place.
- **No background tasks, no websockets.** Plain request/response JSON.
- Python dependencies stay minimal: `fastapi`, `uvicorn`, `pytest` (dev). Nothing else unless the user approves.

## 3. Architecture

```
rozvrh/
├── backend/
│   ├── main.py          # FastAPI app, static file serving, startup
│   ├── db.py            # sqlite3 connection, schema init, all SQL lives here
│   ├── models.py        # Pydantic models (BlockIn, BlockOut, Template...)
│   ├── routes/
│   │   ├── blocks.py    # block CRUD
│   │   ├── weeks.py     # week fetching
│   │   └── templates.py # template CRUD + apply-to-week
│   └── static/          # frontend (served at /)
│       ├── index.html
│       ├── app.js
│       ├── api.js       # all fetch calls live here
│       ├── calendar.js  # grid rendering
│       ├── interact.js  # drag / resize / create interactions
│       └── style.css
├── tests/
│   ├── test_blocks.py
│   ├── test_weeks.py
│   └── test_templates.py
├── AGENTS.md
├── TODO.md
├── README.md            # how to run, API reference
└── requirements.txt
```

### Data model (SQLite)

```sql
CREATE TABLE blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    start       TEXT NOT NULL,   -- ISO 8601 local, e.g. "2026-09-07T14:30"
    end         TEXT NOT NULL,   -- ISO 8601 local
    label       TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '#4a90d9',
    source      TEXT NOT NULL DEFAULT 'ui'   -- 'ui' or 'ics:<uid>' (reserved, see below)
);
-- start < end enforced in validation, not by SQLite

CREATE TABLE templates (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE template_blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,          -- 0=Mon .. 6=Sun
    start_time  TEXT NOT NULL,              -- "HH:MM"
    end_time    TEXT NOT NULL,              -- "HH:MM"
    label       TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '#4a90d9'
);
```

**Key design decision:** blocks are stored as absolute datetimes, NOT as rows inside a "week" table.
Weeks are just a query (`start >= week_start AND start < week_end`). This makes week navigation,
"plan 2–3 weeks ahead", and external API use trivial. Templates store relative day+time so they
can be stamped onto any week.

All times are **local naive ISO strings**. Do not add timezone handling — single user, single server.

**Future: mobile calendar import.** Absolute datetimes map 1:1 to iCalendar `DTSTART`/`DTEND`,
so an ICS/CalDAV import endpoint can be added later without schema changes. The `source`
column is reserved for this (imports set `ics:<uid>` so re-imports can dedupe). Do NOT build
import logic now — just don't add assumptions that would block it.

## 4. API contract

All endpoints under `/api`, JSON in/out. Errors: `{"detail": "..."}` with proper status codes
(FastAPI default). Validation: block `end` must be after `start`; both must be 15-minute-aligned
(`HH:MM` where MM ∈ {00, 15, 30, 45}).

```
GET    /api/weeks/{iso_year}/{iso_week}      -> all blocks overlapping that ISO week
GET    /api/blocks?from={iso}&to={iso}       -> blocks in a datetime range (for external projects)
GET    /api/blocks/todo                      -> unscheduled blocks (source="todo", keeps slot + duration)
POST   /api/blocks                           -> create block, returns it with id
PATCH  /api/blocks/{id}                      -> partial update (any of start/end/label/color/source)
                                             -> start-only patch = move: end = start + original duration
DELETE /api/blocks/{id}                      -> 204

GET    /api/templates                        -> list templates (with their blocks)
POST   /api/templates                        -> create {name, blocks: [...]}
PUT    /api/templates/{id}                    -> replace template blocks
DELETE /api/templates/{id}                    -> 204
POST   /api/templates/{id}/apply/{iso_year}/{iso_week}
       -> copies template blocks into that week; skips slots already occupied
          (overlap = any intersection with an existing block); returns created blocks
```

**Block `source` field:** blocks carry `source` (`"ui"` or `"todo"`). `"todo"` means unscheduled
(parking-lot): the block keeps its slot and duration but is excluded from week/range queries and
listed by `GET /api/blocks/todo`. Scheduling a to-do (any start/end change) flips it back to
`"ui"`. `ics:<uid>` is reserved for future calendar import and is rejected by the API so external
clients cannot forge it. A start-only PATCH means "move, keep duration" — this is what makes
drag-move and to-do scheduling work; external clients should send both start and end if they want
an explicit resize.

**Auth (mandatory):** all `/api/*` requests require an `X-API-Key` header matching env var
`ROZVRH_API_KEY`. Compare with `secrets.compare_digest`. Missing/wrong key -> `401`.
Never log the key. Implement as ONE FastAPI dependency applied to the whole `/api` router.
If the env var is unset at startup, generate a random key and log it once (dev convenience,
visible misconfiguration in prod). The static frontend is served without auth (it contains
no data); `api.js` attaches the key.

**Security posture (internet-facing via Cloudflare):**
- TLS terminates at Cloudflare. The laptop runs a `cloudflared` tunnel — uvicorn binds
  `127.0.0.1` and is never exposed directly. Document this in README.
- Rate limiting / IP rules live at Cloudflare, not in the app (keeps deps minimal).
- Validate all inputs: label length cap (200 chars), color must match `^#[0-9a-fA-F]{6}$`,
  times 15-min aligned. Always use `?` placeholders in SQL — never string interpolation.
- No CORS middleware (frontend is same-origin; external API clients send the key header).
- Secrets only via env vars, never in the repo, never in logs.

## 5. Frontend behavior

- One page. CSS grid: 7 columns (days), rows = 15-min slots (96/day). Time labels on the left.
- Week navigation: prev/next buttons + "today" + a date picker. Default = current week.
- Blocks are divs placed with `grid-row`/`grid-column` on the 15-min grid (chosen over absolute
  positioning in M3: the browser does the row math and M4 drag/resize maps coordinates to rows either way).
- Interactions (Pointer Events, no libraries):
  - Click empty grid → open a small inline form (label, color) → creates a block (default 1h).
  - Drag block body → move (snap 15 min, can cross days).
  - Drag bottom edge → resize (snap 15 min, min 15 min).
  - Click block → popover with edit label/color + delete button.
- Colors: fixed palette of ~8 colors offered in the UI (stored as hex in DB).
- No state library. One `state = {weekOffset/currentWeekStart, blocks}` object; re-render grid
  after every mutation. Keep render functions pure: `render(state) -> DOM`.
- `api.js` attaches `X-API-Key` (from `localStorage`) to every call; on `401` it prompts for
  the key once, stores it, and retries.

## 6. Coding conventions for agents

- **Small modules, one responsibility.** If a file exceeds ~250 lines, split it.
- **No dead code, no commented-out code, no "just in case" abstractions.** If it isn't used, delete it.
- **No try/except that swallows errors.** Let it crash; the user reads logs.
- **Type checks must pass:** `python -m mypy` exits zero before a milestone is done. All backend
  functions are fully annotated; `Any` leaking into returns is an error. If mypy flags an
  "impossible" state (e.g. row missing after INSERT), fix it with `assert` so it crashes
  loudly — never with `cast`/`ignore` to silence it.
- **Pylint must be 10.00/10:** `pylint backend` before a milestone is done. Fix the cause;
  only add a disable to `.pylintrc` if a check genuinely conflicts with project conventions,
  with a comment explaining why. No inline `# pylint: disable` pragmas.
- **Zero warnings policy:** `pytest.ini` sets `filterwarnings = error` with narrow, message-scoped
  ignores ONLY for known third-party deprecations (with a comment explaining each). Any new
  warning — ours or a dependency's — fails the test run. Fix the cause or, if it is genuinely
  third-party, add a narrowly scoped ignore with a comment. Never add broad
  `ignore::DeprecationWarning` lines.
- Every backend route must have at least one pytest covering the happy path and one the error path.
- Frontend: no inline styles in JS where CSS classes work; no `innerHTML` with user data
  (XSS — use `textContent` or createElement).
- Comments: only for *why*, never *what*. Code must be readable without comments.
- Commit messages: imperative, one line (e.g. "Add block PATCH endpoint").
- After finishing a milestone: run the full test suite, fix failures, then request code review.

## 7. Running it

```bash
# dev
uvicorn backend.main:app --reload --port 8000

# prod on the laptop (document in README, provide a systemd unit file)
ROZVRH_DB=/home/USER/.local/share/rozvrh/rozvrh.db uvicorn backend.main:app --port 8000
```

DB path: env var `ROZVRH_DB`, default `./rozvrh.db`. Schema is created on startup if missing.
No migrations system — if the schema changes, write a tiny one-off migration note in README.

## 8. Definition of done (per milestone)

1. `pytest` passes with **zero warnings** (see the zero warnings policy in §6).
1. `python -m mypy` passes with no errors.
1. `pylint backend` rates 10.00/10.
2. App starts with a single command and works in a browser.
3. No TODO/FIXME left in the code from that milestone.
4. README updated if user-facing behavior changed.
