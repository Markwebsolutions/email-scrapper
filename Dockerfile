# Base image
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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python files
COPY ./ /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn aiofiles python-multipart

# Install Node dependencies
RUN npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth googleapis minimist p-limit

# Expose port
EXPOSE 8080

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
