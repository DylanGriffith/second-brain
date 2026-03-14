FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifest and create a stub package so hatchling can resolve deps
COPY pyproject.toml .
RUN mkdir -p src/second_brain && touch src/second_brain/__init__.py

# Install dependencies - cached as long as pyproject.toml doesn't change
RUN uv pip install --system --no-cache .

# Copy actual source (separate layer so dep cache survives source changes)
COPY src/ src/
COPY templates/ templates/

# Reinstall package itself (--no-deps since deps are already installed above)
RUN uv pip install --system --no-cache --no-deps .

ENV SB_VESPA_URL=http://vespa:8080
ENV SB_LOG_LEVEL=INFO

EXPOSE 8000

CMD ["uvicorn", "second_brain.app:app", "--host", "0.0.0.0", "--port", "8000"]
