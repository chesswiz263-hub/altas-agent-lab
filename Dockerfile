FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ATLAS_DB_PATH=/app/data/atlas.db ATLAS_PROJECT_ROOT=/app
COPY pyproject.toml README.md ./
COPY src ./src
COPY static ./static
COPY examples ./examples
RUN pip install --no-cache-dir . && mkdir -p /app/data && useradd -r -u 10001 atlas && chown -R atlas:atlas /app/data
USER atlas
EXPOSE 8000 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/health', timeout=3)"
CMD ["sh", "-c", "exec uvicorn atlas.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
