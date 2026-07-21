FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CATALOG_DIRECTORY=/app/catalog

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY catalog ./catalog

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
