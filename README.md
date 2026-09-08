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
| PATCH  | `/api/blocks/{id}`         | partial update                          |
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
