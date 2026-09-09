# Rozvrh

Single-user weekly calendar, served by FastAPI from a home server.

## Run (dev)

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

If `ROZVRH_API_KEY` is not set, a random key is generated and printed to stdout
on startup. Set it explicitly for anything non-dev:

```bash
ROZVRH_API_KEY=my-secret uvicorn backend.main:app --port 8000
```

All `/api` routes require the header `X-API-Key: <key>`.

## Env vars

| Var             | Default      | Purpose                    |
|-----------------|--------------|----------------------------|
| `ROZVRH_DB`     | `./rozvrh.db`| SQLite database file path  |
| `ROZVRH_API_KEY`| unset        | API key; random one generated and logged once if unset |

## API (M1)

| Method | Path                       | Notes                                   |
|--------|----------------------------|-----------------------------------------|
| GET    | `/api/blocks?from=&to=`    | blocks overlapping the datetime range   |
| POST   | `/api/blocks`              | create a block                          |
| PATCH  | `/api/blocks/{id}`         | partial update; start-only = move (end = start + original duration) |
| DELETE | `/api/blocks/{id}`         | 204                                     |

Times are local naive ISO strings `YYYY-MM-DDTHH:MM`, 15-minute aligned.
Validation: `end > start`, label ≤ 200 chars, color `#RRGGBB`.

## API (M2)

| Method | Path                                          | Notes                                        |
|--------|-----------------------------------------------|----------------------------------------------|
| GET    | `/api/weeks/{iso_year}/{iso_week}`            | blocks *overlapping* that ISO week           |
| GET    | `/api/templates`                              | list templates with their blocks             |
| POST   | `/api/templates`                              | create `{name, blocks: [...]}`               |
| PUT    | `/api/templates/{id}`                         | replace template name + blocks               |
| DELETE | `/api/templates/{id}`                         | 204, deletes its blocks too                  |
| POST   | `/api/templates/{id}/apply/{iso_year}/{iso_week}` | stamp template into that week            |

Template blocks use relative times: `{day_of_week: 0-6 (Mon=0), start_time: "HH:MM",
end_time: "HH:MM", label, color}`. Apply copies each template block to the target
week's corresponding day and **skips slots that overlap any existing block** in that
week; it returns the blocks that were created (re-applying the same template is a no-op).
Week 53 is only valid for years that actually have one (e.g. 2026 yes, 2025 no).

## API (M4.5) — to-do blocks

| Method | Path                       | Notes                                        |
|--------|----------------------------|----------------------------------------------|
| GET    | `/api/blocks/todo`         | unscheduled (parking-lot) blocks, newest first |

A to-do block is a normal block with `source: "todo"`. It keeps a slot and
duration (start/end) like any block, but is hidden from week and range queries.
Create one with `POST /api/blocks` and `"source": "todo"`. Scheduling one means
`PATCH`ing `start` (duration is preserved) or `start` + `end` — the server flips
`source` back to `ui`. Unscheduling means `PATCH`ing `{"source": "todo"}`; the
slot and duration survive the round-trip. The `source` field only accepts `ui`
and `todo` (`ics:<uid>` is reserved for future calendar import and cannot be set
via the API).

## Tests

```bash
python -m pytest
```

## Frontend

Vanilla JS (ES modules), no build step. One page: a 7-day CSS-grid calendar
(15-min rows), week navigation (prev/next/today/date picker), and a to-do column.

- **Interactions:** click an empty grid slot to create a block (default 1h); drag
  the block body to move (snaps to 15 min, can cross days, grab point is kept);
  drag the bottom edge to resize (the edge follows the pointer, minimum 15 min);
  click a block to edit label/color or delete. Every mutation re-fetches and
  re-renders from server state; failed saves show an error banner in the toolbar.
- **To-do column:** create-as-todo from the grid editor, tap a card to edit/delete,
  drag a card onto the grid to schedule (duration preserved), drag a block onto
  the column (or use the editor's To-do button) to unschedule.
- **Templates:** the toolbar Templates button opens a panel to save the current
  week's blocks as a named template, list existing ones (with their day/time
  summary), apply a template to the week being viewed, and delete templates.
  Applying skips slots occupied by existing blocks and reports what was skipped
  ("2 added, skipped (occupied): Standup, Gym").
- Blocks show their duration (e.g. `2h 30m`, correct across midnight).
- The API key is kept in `localStorage`; on 401 the page prompts for it and retries.
- Mobile: the grid scrolls horizontally with a minimum day width, the to-do
  column keeps a fixed size, the editor is clamped to the viewport.

## Schema note

M4.5 started using the `source` column (`ui`/`todo`) that was reserved in the
original schema. No migration needed — the column existed from day one.
