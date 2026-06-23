# syntax=docker/dockerfile:1
#
# Container image for the Sentinel-Graph dashboard.
# Build:  docker build -t sentinel-graph .
# Run:    docker run -p 8501:8501 --env-file .env sentinel-graph
#
# This makes the app portable to any container host (Render, Railway, Cloud Run,
# AWS App Runner/ECS, Azure Container Apps, Fly.io, Kubernetes, a plain VPS, ...).

# ── Base image ────────────────────────────────────────────────────────────────
# Python 3.11 (slim) — pydantic-ai 1.x requires 3.10+, and 3.11 is the verified target.
FROM python:3.11-slim

# Keep Python lean and logs unbuffered (so container logs appear in real time).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ── Dependencies (separate layer so it's cached unless requirements change) ────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY agents/ ./agents/
COPY src/ ./src/
COPY .streamlit/config.toml ./.streamlit/config.toml

# Run as a non-root user — a basic security best practice for containers.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

# Streamlit serves on 8501 by default. Cloud hosts often inject their own $PORT.
EXPOSE 8501
ENV PORT=8501

# Health probe against Streamlit's built-in endpoint (most hosts use their own too).
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Shell form so ${PORT} expands; `exec` makes Streamlit PID 1 so it receives
# SIGTERM directly and shuts down gracefully. Bind to 0.0.0.0 to be reachable.
CMD exec streamlit run src/dashboard.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true
