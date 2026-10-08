FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

EXPOSE 8000

ENV DJANGO_DEBUG=0
# Prometheus multiprocess mode: gunicorn workers write metrics here; /metrics merges them
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
RUN mkdir -p $PROMETHEUS_MULTIPROC_DIR  # every process (web, worker, manage.py) needs it to exist

CMD ["sh", "-c", "mkdir -p $PROMETHEUS_MULTIPROC_DIR && python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py seed_data && { [ -z \"$DJANGO_SUPERUSER_USERNAME\" ] || python manage.py createsuperuser --noinput || true; } && rm -rf $PROMETHEUS_MULTIPROC_DIR/* && gunicorn trustsite.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
