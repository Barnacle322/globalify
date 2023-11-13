FROM python:3.12.0-alpine

RUN pip install Werkzeug==3.0.1 \
    Flask==3.0.0 \
    Flask-SQLalchemy==3.1.1 \
    Flask-Login==0.6.3 \
    Flask-Migrate==4.0.5 \
    Flask-WTF==1.2.1 \
    psycopg-binary==3.1.12 \
    Authlib==1.2.1 \
    requests==2.31.0 \
    pycountry==22.3.5 \
    gunicorn==20.1.0 \
    google-cloud-storage==2.13.0 \ 
    pillow==10.0.1 \
    stripe==7.3.0 \
    faker==19.13.0 \
    sendgrid==6.10.0 \
    --no-cache-dir

COPY src/ app/
WORKDIR /app

ENV PORT 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 project:application