FROM python:3.12-slim

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @playwright/mcp@0.0.75 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "openai-agents[litellm]>=0.22.3,<1.0.0" \
    "fastapi>=0.136.1,<1.0.0" \
    "uvicorn[standard]>=0.31.1,<1.0.0" \
    "playwright>=1.54.0,<2.0.0" \
    "python-dotenv>=1.1.1,<2.0.0" \
    "httpx>=0.28.1,<1.0.0"

RUN python -m playwright install --with-deps chromium

COPY backend/services/agents/researcher_agent/ /app/backend/services/agents/researcher_agent/

EXPOSE 8000
CMD ["uvicorn", "backend.services.agents.researcher_agent.server:app", "--host", "0.0.0.0", "--port", "8000"]