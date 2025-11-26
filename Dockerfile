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
    xdg-utils \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set Puppeteer env
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Create app directory
WORKDIR /app

# Copy Python backend
COPY . .

# Install Node dependencies
RUN npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth googleapis minimist p-limit

# Install Python dependencies
RUN pip install fastapi uvicorn aiofiles

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
