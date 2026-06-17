# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the shared domain package first (changes least often).
COPY shared/ /opt/shared/
RUN pip install /opt/shared

# Service deps.
COPY services/payments/requirements.txt .
RUN pip install -r requirements.txt

# Service code.
COPY services/payments/app ./app

EXPOSE 8004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
