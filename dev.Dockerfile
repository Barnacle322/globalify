FROM python:3.12.0-alpine

COPY src/ app/
COPY pyproject.toml /app
COPY poetry.lock /app

WORKDIR /app

RUN pip install poetry
RUN poetry install --with dev --no-root --no-directory

CMD exec poetry run flask run --host=0.0.0.0