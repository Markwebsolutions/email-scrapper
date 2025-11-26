# Base image with Python + Node
FROM nikolaik/python-nodejs:python3.10-nodejs18

# Install Chromium dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libx11-xcb1 \
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# Set chromium path for puppeteer
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Install Node.js dependencies
COPY package*.json ./
RUN npm install

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose default port
EXPOSE 8080

# Run Uvicorn with a shell to expand $PORT, fallback to 8080
CMD sh -c 'uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}'
