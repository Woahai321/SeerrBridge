# Multi-stage build for production optimization
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.10-slim

# Create non-root user for security
RUN groupadd -r seerrbridge && useradd -r -g seerrbridge seerrbridge

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    libnss3 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    libgbm-dev \
    libgtk-3-0 \
    libx11-xcb1 \
    libxtst6 \
    xdg-utils \
    libglib2.0-0 \
    libdrm2 \
    libxrandr2 \
    ca-certificates \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install browser and driver based on architecture
RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then \
        PLATFORM="linux64" && \
        CHROME_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
        jq -r '.channels.Stable.version') && \
        CHROME_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
        jq -r ".channels.Stable.downloads.chrome[] | select(.platform == \"$PLATFORM\") | .url") && \
        echo "Downloading Chrome version ${CHROME_VERSION} for $PLATFORM from: $CHROME_URL" && \
        wget -O /tmp/chrome-$PLATFORM.zip $CHROME_URL && \
        unzip /tmp/chrome-$PLATFORM.zip -d /opt/ && \
        mv /opt/chrome-$PLATFORM /opt/chrome && \
        ln -sf /opt/chrome/chrome /usr/bin/google-chrome && \
        chmod +x /usr/bin/google-chrome && \
        rm -f /tmp/chrome-$PLATFORM.zip && \
        CHROMEDRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
        jq -r ".channels.Stable.downloads.chromedriver[] | select(.platform == \"$PLATFORM\") | .url") && \
        echo "Downloading ChromeDriver for $PLATFORM from: $CHROMEDRIVER_URL" && \
        wget -O /tmp/chromedriver-$PLATFORM.zip $CHROMEDRIVER_URL && \
        unzip /tmp/chromedriver-$PLATFORM.zip -d /usr/local/bin/ && \
        mv /usr/local/bin/chromedriver-$PLATFORM/chromedriver /usr/local/bin/chromedriver && \
        chmod +x /usr/local/bin/chromedriver && \
        rm -rf /tmp/chromedriver-$PLATFORM.zip /usr/local/bin/chromedriver-$PLATFORM; \
    elif [ "$arch" = "aarch64" ]; then \
        echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list && \
        echo "deb http://deb.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list && \
        apt-get update && \
        apt-get install -y --no-install-recommends chromium chromium-driver && \
        ln -sf /usr/bin/chromium /usr/bin/google-chrome && \
        ln -sf /usr/bin/chromium-driver /usr/local/bin/chromedriver && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        echo "Unsupported architecture: $arch"; exit 1; \
    fi

# Copy Python packages from builder stage to /root/.local (running as root)
COPY --from=builder /root/.local /root/.local

# Set working directory
WORKDIR /app

# Copy application code (running as root, no chown needed)
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R seerrbridge:seerrbridge /app

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
ENV RUNNING_IN_DOCKER=true
ENV PYTHONPATH=/app
ENV PATH=/root/.local/bin:$PATH

# Run as root like the old setup for Chrome compatibility
# USER seerrbridge

# Expose the application port
EXPOSE 8777

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8777/status || exit 1

# Run the application with setup wait
CMD ["sh", "-c", "python scripts/wait-for-setup.py"]
