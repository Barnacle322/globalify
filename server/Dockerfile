FROM python:3.12.0-alpine

RUN pip install Flask==2.3.3 \
    Flask-SQLalchemy==3.1.1 \
    Flask-Login==0.6.2 \
    Flask-Migrate==4.0.5 \
    Flask-WTF==1.2.1 \
    psycopg2-binary==2.9.9 \
    Authlib==1.2.1 \
    requests==2.31.0 \
    pycountry==22.3.5 \
    gunicorn==21.2.0 \
    google-cloud-storage==2.11.0 \ 
    pillow==10.0.1 \
    stripe==6.6.0 \
    faker==19.6.2 \
    --no-cache-dir

COPY src/ app/
WORKDIR /app

ENV PORT 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 project:application