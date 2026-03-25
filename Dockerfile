FROM python:3.11-alpine AS base

# --- builder
FROM base AS builder
WORKDIR /app
RUN pip install uv
COPY futurehealth /src/futurehealth
COPY pyproject.toml README.md /src/
RUN uv pip install --target=/app '/src[cli]'

# --- main
FROM base
COPY --from=builder /app /app
ENV PYTHONPATH=/app

ENTRYPOINT ["python3", "-m", "futurehealth"]
