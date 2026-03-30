# Multi-stage Docker build for FastAPI with UV
# Builder stage - compile dependencies
FROM python:3.10-slim as builder

# Install system dependencies needed for compilation
RUN apt-get update && apt-get install -y gcc g++ gfortran git

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy UV configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies with UV (much faster than pip)
RUN uv sync --frozen --no-cache

# Runtime stage - minimal footprint
FROM python:3.10-slim as runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y libopenblas0 liblapack3 && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Set environment variables for FastAPI
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Expose the port FastAPI will run on
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command to start FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]