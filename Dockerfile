FROM python:3.11-alpine AS base

# --- builder
FROM base AS builder
WORKDIR /app
WORKDIR /

COPY Pipfile.lock .
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

# --- main
FROM base
COPY --from=builder /app /app
ENV PYTHONPATH=/app
COPY futurehealth /app/futurehealth

ENTRYPOINT ["python3", "-m", "futurehealth"]
