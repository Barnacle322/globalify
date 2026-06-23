# Deploying with Docker Compose

`docker-compose.yml` runs the full Globalify stack on one host: the app (granian
WSGI), **Typesense** (search), and **Postgres** (database). It's suited to a single
self-hosted box.

## Services

| Service | Image | Role | Persistence |
|---|---|---|---|
| `app` | built from `Dockerfile` | Flask app via granian on container port 80 | — |
| `typesense` | `typesense/typesense:30.2` | search index | `typesense-data` volume |
| `db` | `postgres:16-alpine` | source-of-truth database | `pg-data` volume |

Typesense and Postgres publish to `127.0.0.1` only (reachable by host tooling like
`flask reindex`/`psql`, not the public interface). Only the `app` port is exposed
publicly (`${APP_PORT:-8000}` → 80).

## Configuration

Secrets come from `.env` (loaded via `env_file`). Service wiring is set explicitly
in `docker-compose.yml` under the `app` service's `environment:` and **overrides**
`.env`, so the app always talks to the sibling `db`/`typesense` and runs in
production mode regardless of local `.env` values:

- `FLASK_ENV=production`
- `_DATABASE_URL=postgresql+psycopg://globalify:${POSTGRES_PASSWORD:-globalify}@db:5432/globalify`
- `_TYPESENSE_HOST=typesense`

Override these at deploy time:

| Compose var | Default | Purpose |
|---|---|---|
| `APP_PORT` | `8000` | Host port for the app |
| `POSTGRES_PASSWORD` | `globalify` | Postgres password (set a real one in prod) |
| `_TYPESENSE_API_KEY` | `xyz` | Typesense API key (set a real one in prod; read from `.env`) |

## Quickstart

```bash
cp .env.example .env          # fill SECRET_KEY (required); GEMINI_API_KEY for semantic search
docker compose up -d --build

# First-time init — create tables, seed demo data, build the Typesense index:
docker compose run --rm app uv run flask --app project setup

open http://localhost:8000
```

## Real data (instead of the demo seed)

`flask setup` is destructive (drops + recreates + seeds demo data). For real data:

```bash
# 1. Apply DB migrations (requires migrations/ in the image — see caveat below)
docker compose run --rm app uv run flask --app project db upgrade
# 2. Build/refresh the Typesense index from the DB (non-destructive)
docker compose run --rm app uv run flask --app project reindex
# 3. Grow the directory from public sources
docker compose run --rm app uv run flask --app project collect edgar --limit 50
```

> **Caveat:** the current `Dockerfile` copies only `src/`, so `migrations/` is not in
> the image. For migration-based deploys, add `COPY migrations/ /app/migrations/` to the
> `Dockerfile`. The demo `flask setup` path uses `create_all` and does not need migrations.

## Semantic search

Set in `.env` (then recreate the index):

```
_EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=<your key>      # free tier is sufficient; embeddings run app-side
```

```bash
docker compose run --rm app uv run flask --app project reindex   # re-embeds all docs
```

Embeddings run **in the app** (not in Typesense), so this adds no model to the
Typesense/host footprint. When the provider is `none` (default) or a Gemini call
fails, search transparently falls back to keyword-only. See
[`search-embeddings.md`](search-embeddings.md) for details and threshold tuning.

## Operations

```bash
docker compose ps                       # status
docker compose logs -f app              # app logs
docker compose up -d --build app        # redeploy after a code change
docker compose down                     # stop (volumes preserved)
docker compose down -v                  # stop AND wipe data volumes
```
