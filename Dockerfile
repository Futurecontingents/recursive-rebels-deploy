FROM python:3.12-slim

WORKDIR /app

COPY Backend/ /app/Backend/
COPY map.html /app/
COPY map.js /app/
COPY ui.js /app/
COPY style.css /app/
COPY data.js /app/

RUN pip install --no-cache-dir Flask gunicorn requests

EXPOSE 8080

CMD ["sh", "-c", "cd /app/Backend && exec gunicorn app:app --bind 0.0.0.0:${PORT:-8080}"]
