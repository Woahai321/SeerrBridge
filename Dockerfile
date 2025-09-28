FROM python:3.10
WORKDIR /app
# Install required dependencies
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
    jq && \
    rm -rf /var/lib/apt/lists/*
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
        chmod +x /usr/bin/google-chrome; \
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
# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
ENV RUNNING_IN_DOCKER=true
# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy the application code
COPY . .
# Expose the application port
EXPOSE 8777
# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8777"]
