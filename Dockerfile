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
    jq

# Download and install Chrome (latest stable version)
RUN CHROME_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
    jq -r '.channels.Stable.downloads.chrome[] | select(.platform == "linux64") | .url') && \
    echo "Downloading Chrome from: $CHROME_URL" && \
    wget -O /tmp/chrome-linux64.zip $CHROME_URL && \
    unzip /tmp/chrome-linux64.zip -d /opt/ && \
    mv /opt/chrome-linux64 /opt/chrome && \
    ln -sf /opt/chrome/chrome /usr/bin/google-chrome && \
    chmod +x /usr/bin/google-chrome

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
ENV RUNNING_IN_DOCKER=true

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the application port (if needed)
EXPOSE 8777

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8777"]
