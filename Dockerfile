# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (kept minimal). pdfplumber pulls in pdfminer, and may use some fonts.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install python deps first for better layer caching
COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --upgrade pip \
  && python -m pip install --no-cache-dir ".[web]"

EXPOSE 8080

# Many hosting platforms provide the port via the PORT environment variable.
ENV HOST=0.0.0.0 \
    PORT=8080

CMD ["python", "-m", "uvicorn", "csv2json.web:app", "--host", "0.0.0.0", "--port", "8080"]
