FROM python:3.12.0-alpine as python-base


COPY src/ app/
COPY pyproject.toml /app
COPY poetry.lock /app
COPY poetry.toml /app

WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --without dev --no-root
RUN pip install gunicorn==20.1.0

ENV PORT 8080

CMD exec poetry run gunicorn --bind :$PORT --workers 1 --threads 8 project:application