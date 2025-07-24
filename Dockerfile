FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    chromium \
    chromium-driver \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium (optional, if your code uses these)
ENV CHROMIUM_BIN=/usr/bin/chromium \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Default command to run your bot
CMD gunicorn app:app & python3 main.py & python3 ping.py
