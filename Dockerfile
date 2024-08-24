FROM python:3.12-slim-bookworm

COPY src/ app/
COPY pyproject.toml /app
COPY uv.lock /app
COPY README.md /app

WORKDIR /app

RUN pip install uv
RUN uv sync
RUN uv pip install granian
RUN uv pip install more_itertools
RUN rm -rf /root/.cache/pip/*

ENV PORT 80

CMD exec uv run granian --interface wsgi --port $PORT --host 0.0.0.0 --workers 5 --threads 8 project:application