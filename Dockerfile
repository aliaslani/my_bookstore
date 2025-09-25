FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install uv
RUN uv pip install --system django psycopg2-binary python-decouple djangorestframework django-redis celery

ENV PYTHONUNBUFFERED=1

EXPOSE 8000
