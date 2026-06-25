FROM python:3.14-slim-bookworm

COPY src/ app/
COPY migrations/ /app/migrations/
COPY pyproject.toml /app
COPY uv.lock /app
COPY README.md /app

WORKDIR /app

RUN pip install uv
RUN uv sync --frozen --no-install-project
RUN rm -rf /root/.cache/pip/*

ENV PORT=80

# Granian tuning. Defaults are conservative for small instances; override any of
# these per host via env (they are granian's native GRANIAN_* variables):
#   GRANIAN_WORKERS           ~= vCPU count (each worker loads a full copy of the app)
#   GRANIAN_BLOCKING_THREADS  per-worker concurrency for the blocking WSGI app (DB + Typesense I/O)
#   GRANIAN_BACKPRESSURE      max requests processed concurrently per worker
ENV GRANIAN_WORKERS=2 \
    GRANIAN_BLOCKING_THREADS=4 \
    GRANIAN_BACKPRESSURE=64

# The app listens here. Dokploy/Traefik must route to this same port (set the
# container port in the Dokploy domain settings to match, default 80).
EXPOSE 80

CMD exec uv run granian --interface wsgi --host 0.0.0.0 --port $PORT project:application