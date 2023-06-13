FROM python:3.11.4-alpine

RUN pip install Flask==2.2.2 Flask-SQLalchemy==3.0.2 Flask-Login==0.6.2 psycopg2-binary==2.9.5 Jinja2==3.1.2 gunicorn==20.1.0 --no-cache-dir

COPY src/ app/
WORKDIR /app

ENV PORT 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 project:application