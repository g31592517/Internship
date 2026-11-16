# One container for the whole platform: the FastAPI backend serves the API (/api/...) and the built React app (/).

# ---- 1. build the React frontend ---------------------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. Python backend --------------------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INTERNSHIP_DATA_DIR=/var/data
WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src/ src/
COPY --from=web /web/dist frontend/dist

# SQLite database + uploaded CVs live in $INTERNSHIP_DATA_DIR. On Render, mount a persistent disk there,
# otherwise they are wiped on every deploy/restart.
RUN mkdir -p /var/data

# Render provides $PORT (default 10000) and requires binding to 0.0.0.0. One worker on purpose: the search
# cache and the scrape limiter live in process memory, and SQLite prefers a single writer.
EXPOSE 10000
CMD ["sh", "-c", "uvicorn api.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
