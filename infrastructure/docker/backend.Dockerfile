FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# pip vendors setuptools 70.3.0 (CVE-2025-47273, declared in pip/_vendor/bom.cdx.json); the runtime never uses pip, so drop it.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall -y pip

COPY . .
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]