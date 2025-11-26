# ----------------------------------------------------
# Base image: Python + Node (your code requires both)
# ----------------------------------------------------
FROM nikolaik/python-nodejs:python3.10-nodejs18

# ----------------------------------------------------
# Install full Chromium + all required dependencies
# (Puppeteer MUST have these to run on Railway)
# ----------------------------------------------------
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    xvfb \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libcups2 \
    libxshmfence1 \
    xdg-utils \
    wget \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Puppeteer expects this
ENV PUPPETEER_EXECUTABLE_PATH="/usr/bin/chromium"

# ----------------------------------------------------
# Set working directory
# ----------------------------------------------------
WORKDIR /app

# ----------------------------------------------------
# Install Node dependencies
# (Puppeteer is installed here)
# ----------------------------------------------------
COPY package*.json ./
RUN npm install --omit=dev

# ----------------------------------------------------
# Install Python dependencies
# ----------------------------------------------------
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------
# Copy entire project
# ----------------------------------------------------
COPY . .

# Ensure storage directory exists
RUN mkdir -p storage

# ----------------------------------------------------
# Expose port
# ----------------------------------------------------
EXPOSE 8080

# ----------------------------------------------------
# Run your Python app exactly as written
# (your code uses "python", so we keep that)
# ----------------------------------------------------
CMD ["python", "main.py"]
