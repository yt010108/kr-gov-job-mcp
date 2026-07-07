FROM python:3.12-slim

ARG APP_SOURCE_REF=unknown
ARG APP_REVISION=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_SOURCE_REF=${APP_SOURCE_REF} \
    APP_REVISION=${APP_REVISION}

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "python -m kr_gov_job_mcp.server --http --host 0.0.0.0 --port ${PORT:-8000}"]
