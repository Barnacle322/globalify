FROM python:3.11.4-alpine

RUN pip install Flask==2.3.2 Flask-SQLalchemy==3.0.3 Flask-Login==0.6.2 Flask-Migrate==4.0.4 psycopg2-binary==2.9.6 Jinja2==3.1.2 Authlib==1.2.1 requests==2.31.0 pycountry gunicorn==20.1.0 --no-cache-dir

COPY src/ app/
WORKDIR /app

ENV PORT 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 project:application