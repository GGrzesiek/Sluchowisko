FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 DEBUG=0

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY manage.py ./
COPY config config
COPY transit transit
COPY facts facts
COPY stories stories

RUN useradd --create-home app
USER app
CMD exec gunicorn config.wsgi --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 60
