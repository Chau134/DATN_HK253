# Managed-model image: Cohere embeddings on Bedrock and Google ranking run
# remotely, while YOLO is disabled. No CUDA, PyTorch, Transformers, or
# Ultralytics are installed.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_PORT=8000

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install .

# Run as a non-root user.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/ready').status==200 else 1)"

CMD ["sh", "-c", "python -m ecommerce_search_assistant.infrastructure.qdrant && python -m uvicorn ecommerce_search_assistant.main:app --host 0.0.0.0 --port ${PORT:-$APP_PORT}"]
