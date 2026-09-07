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

## Tests

```bash
python -m pytest
```
