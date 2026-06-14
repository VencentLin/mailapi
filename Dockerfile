FROM node:20-bookworm AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
COPY alembic.ini ./alembic.ini
RUN pip install --no-cache-dir .

COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN sed -i 's/\r$//' ./docker/entrypoint.sh \
    && chmod +x ./docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker/entrypoint.sh"]
