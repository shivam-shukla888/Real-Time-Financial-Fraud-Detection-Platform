# Multi-stage CPU-friendly Dockerfile for Fraud Detection API
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/data /app/artifacts /app/reports && \
    chown -R appuser:appuser /app

# Copy installed python wheels from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code and artifacts
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser configs/ ./configs/
COPY --chown=appuser:appuser artifacts/ ./artifacts/
COPY --chown=appuser:appuser data/sample_transactions.csv ./data/sample_transactions.csv

USER appuser

EXPOSE 8010

# Health check probe
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8010"]
