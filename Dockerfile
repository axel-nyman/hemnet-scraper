# Use buildx for multi-architecture support
FROM --platform=$TARGETPLATFORM python:3.9-slim AS builder

# Set work directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements in a separate layer
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Start a new stage
FROM --platform=$TARGETPLATFORM python:3.9-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder stage
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .

# Install Python packages from wheels
RUN pip install --no-cache /wheels/*

# Install Playwright
RUN playwright install webkit
RUN playwright install-deps webkit

# Copy application code
COPY src/ ./src

# Create logs directory
RUN mkdir -p /app/logs

# Set the default command
CMD ["python", "src/main.py"]