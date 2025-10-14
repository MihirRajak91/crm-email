# Stage 1: Builder
FROM python:3.12-slim as builder

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install build dependencies required for Poetry packages (weasyprint, pdf2image, polyglot, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    pkg-config \
    libffi-dev \
    libcairo2-dev \
    libgdk-pixbuf-2.0-dev \
    libpango1.0-dev \
    libicu-dev \
    libmagic-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Disable venv and install dependencies (excluding dev)
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction --no-ansi --no-root

# Copy source code
COPY . .

# Stage 2: Runtime
FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install runtime OS deps needed at execution time for document processing
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libffi8 \
    libicu72 \
    libmagic1 \
    poppler-utils \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Copy site-packages and bin from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app source code
COPY --from=builder /app /app

# Optional: install Poetry again if you need it (not necessary here)
# RUN curl -sSL https://install.python-poetry.org | python3 - && \
#     ln -s /root/.local/bin/poetry /usr/local/bin/poetry

EXPOSE 8000

# Use uvicorn directly, since it's now globally available
CMD ["uvicorn", "crm.main:app", "--host", "0.0.0.0", "--port", "8000"]
