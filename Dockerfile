# ---- Base image ---------------------------------------------------------
# Official, trusted Python image. '-slim' = fewer packages = smaller image
# and fewer vulnerabilities for the scanner to complain about.
FROM python:3.12-slim

# Don't write .pyc files; print logs immediately (so `kubectl logs` is live)
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

# Copy requirements first: Docker caches this layer, so rebuilds are fast
# unless dependencies change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as a non-root user (security best practice)
RUN useradd --system --uid 10001 appuser
USER 10001

# Build-time metadata so /version tells the truth about the running release
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
ENV APP_VERSION=${APP_VERSION} GIT_SHA=${GIT_SHA} PORT=8000

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-m", "app.healthcheck"]

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 app.main:app"]
