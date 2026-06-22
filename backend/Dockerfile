# ── Builder stage: compile dependencies ─────────────────────
FROM python:3.13-alpine AS builder

WORKDIR /build

RUN apk add --no-cache build-base postgresql-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -name '*.pyc' -delete


# ── Development stage (hot-reload, code mounted via volume) ─
FROM python:3.13-alpine AS development

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apk add --no-cache build-base postgresql-dev libffi-dev openssl-dev curl

COPY --from=builder /root/.local /usr/local

RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup -h /app -s /sbin/nologin && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/api/v1/health || exit 1


# ── Production stage ────────────────────────────────────────
FROM python:3.13-alpine AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime libs only (no build-base, no gcc)
RUN apk add --no-cache postgresql-libs curl

# Non-root user
RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup -h /app -s /sbin/nologin

# Copy installed packages from builder
COPY --from=builder /root/.local /usr/local

# Application code (no tests, no .env)
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY scripts/ ./scripts/

# Entrypoint runs Alembic migrations before starting
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
