FROM nikolaik/python-nodejs:python3.10-nodejs18

# Install Chromium and dependencies (Debian-compatible)

RUN apt-get update && apt-get install -y 
chromium 
chromium-driver 
fonts-liberation 
libnss3 
libatk-bridge2.0-0 
libatk1.0-0 
libx11-xcb1 
xdg-utils && 
rm -rf /var/lib/apt/lists/*

# Puppeteer executable path

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Set working directory

WORKDIR /app

# Install Node.js dependencies

COPY package*.json ./
RUN npm install

# Install Python dependencies

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code

COPY . .

# Expose default port

EXPOSE 8080

# Run the app using shell form so $PORT is expanded

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
