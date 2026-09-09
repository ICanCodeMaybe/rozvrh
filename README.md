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

## Production setup (home server behind Cloudflare)

TLS terminates at Cloudflare; the laptop is never exposed directly. Uvicorn binds
`127.0.0.1` and the `cloudflared` tunnel forwards the public hostname to it.

1. Install: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
2. Create a data dir and set a real API key:

   ```bash
   mkdir -p ~/.local/share/rozvrh
   export ROZVRH_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
   ```

3. Copy `rozvrh.service` and `cloudflared.service` to `/etc/systemd/system/`, edit
   `User=`, `Environment=` (put the generated key in `rozvrh.service`) and the paths,
   then:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now cloudflared.service rozvrh.service
   ```

4. Cloudflare side (one-time):

   ```bash
   cloudflared tunnel login
   cloudflared tunnel create rozvrh
   cloudflared tunnel route dns rozvrh calendar.example.com
   ```

   Put the tunnel credentials under `/etc/cloudflared/` and configure the ingress
   in `/etc/cloudflared/config.yml`:

   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /etc/cloudflared/<tunnel-id>.json
   ingress:
     - hostname: calendar.example.com
       service: http://127.0.0.1:8000
     - service: http_status:404
   ```

The app itself has no rate limiting or IP rules; configure those in the
Cloudflare dashboard (WAF / rate limiting rules) if wanted — keeps the app
dependencies minimal.

## Env vars

| Var             | Default      | Purpose                    |
|-----------------|--------------|----------------------------|
| `ROZVRH_DB`     | `./rozvrh.db`| SQLite database file path  |
| `ROZVRH_API_KEY`| unset        | API key; random one generated and logged once if unset |



## API reference

All endpoints are under `/api`, JSON in/out, and require the header
`X-API-Key: <key>`. Missing or wrong key → `401`. Validation errors → `422`
with `{"detail": ...}`. Missing resources → `404`.

Rules for block times: local naive ISO strings `YYYY-MM-DDTHH:MM`,
15-minute aligned (`MM` ∈ `00/15/30/45`), and `end > start`. Labels ≤ 200 chars,
colors match `#RRGGBB`. The `source` field only accepts `ui` and `todo`
(`ics:<uid>` is reserved for future calendar import and cannot be set via the
API).

### Blocks

| Method | Path                       | Notes                                   |
|--------|----------------------------|-----------------------------------------|
| GET    | `/api/blocks?from=&to=`    | blocks overlapping the datetime range (to-dos excluded) |
| GET    | `/api/blocks/todo`         | unscheduled (parking-lot) blocks, newest first |
| POST   | `/api/blocks`              | create a block, 201 with the stored block |
| PATCH  | `/api/blocks/{id}`         | partial update; start-only = move (end = start + original duration) |
| DELETE | `/api/blocks/{id}`         | 204, 404 if unknown                     |

POST body: `{"start", "end", "label" (opt), "color" (opt), "source" (opt: "ui"/"todo")}`.
PATCH accepts any subset of the same fields (empty patch → 422). A to-do that
gets a `start`/`end` change is scheduled again (`source` flips to `ui`); any
`start`/`end` change on a to-do preserves the slot/duration otherwise.

### Weeks

| Method | Path                            | Notes                                   |
|--------|---------------------------------|-----------------------------------------|
| GET    | `/api/weeks/{iso_year}/{iso_week}` | blocks *overlapping* that ISO week (to-dos excluded) |

`iso_week` must be 1..53 and week 53 only for years that have one; invalid
year/week → 422.

### Templates

| Method | Path                                          | Notes                                        |
|--------|-----------------------------------------------|----------------------------------------------|
| GET    | `/api/templates`                              | list templates with their blocks             |
| POST   | `/api/templates`                              | create `{name, blocks: [...]}`               |
| PUT    | `/api/templates/{id}`                         | replace template name + blocks               |
| DELETE | `/api/templates/{id}`                         | 204, deletes its blocks too                  |
| POST   | `/api/templates/{id}/apply/{iso_year}/{iso_week}` | stamp template into that week            |

Template blocks use relative times: `{day_of_week: 0-6 (Mon=0), start_time:
"HH:MM", end_time: "HH:MM", label (opt), color (opt)}` — times must also be
15-minute aligned, `end_time > start_time`, name 1..100 chars. Apply copies each
template block to the target week's corresponding day and **skips slots that
overlap any existing block** in that week; it returns the blocks that were
created (re-applying the same template is a no-op).

#### curl examples

```bash
KEY=...  # value of ROZVRH_API_KEY
BASE=http://127.0.0.1:8000

# create a block
curl -s -X POST "$BASE/api/blocks" -H "X-API-Key: $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"start":"2026-09-07T14:30","end":"2026-09-07T15:30","label":"Gym"}'

# list blocks in a range
curl -s "$BASE/api/blocks?from=2026-09-07T00:00&to=2026-09-08T00:00" -H "X-API-Key: $KEY"

# move (start-only patch keeps the duration)
curl -s -X PATCH "$BASE/api/blocks/1" -H "X-API-Key: $KEY" \
  -H 'Content-Type: application/json' -d '{"start":"2026-09-08T09:00"}'

# park / unpark as to-do
curl -s -X PATCH "$BASE/api/blocks/1" -H "X-API-Key: $KEY" \
  -H 'Content-Type: application/json' -d '{"source":"todo"}'
curl -s "$BASE/api/blocks/todo" -H "X-API-Key: $KEY"

# current week
curl -s "$BASE/api/weeks/2026/37" -H "X-API-Key: $KEY"

# create a template and apply it to a week
curl -s -X POST "$BASE/api/templates" -H "X-API-Key: $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Standard","blocks":[{"day_of_week":0,"start_time":"09:00","end_time":"09:30","label":"Standup"}]}'
curl -s -X POST "$BASE/api/templates/1/apply/2026/40" -H "X-API-Key: $KEY"

# delete
curl -s -X DELETE "$BASE/api/blocks/1" -H "X-API-Key: $KEY" -o /dev/null -w '%{http_code}\n'
```

Without `-H "X-API-Key: ..."` every one of these returns `401`.

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

M6 added 15-minute alignment validation for template `start_time`/`end_time`
(already required for blocks). Templates stored earlier with non-aligned times
remain readable; applying them creates blocks outside the 15-minute grid.
Re-create such templates if strict alignment matters.
