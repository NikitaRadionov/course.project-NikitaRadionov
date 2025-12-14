# BUILD STAGE
FROM python:3.11-slim AS build
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./

RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

#RUNTIME STAGE
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser

COPY --from=build /venv /venv
COPY app ./app

RUN mkdir -p /app/db && chown -R appuser:appuser /app/db

ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
