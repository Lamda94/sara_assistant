FROM node:22-slim

# Playwright deps + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libxshmfence1 fonts-liberation curl \
    && rm -rf /var/lib/apt/lists/*

# Career-ops
WORKDIR /career-ops
COPY career-ops/package.json ./
RUN npm install --prefer-offline
COPY career-ops/ .
RUN npx playwright install chromium

# Ensure data directories exist
RUN mkdir -p data output reports jds interview-prep batch/tracker-additions

# API wrapper
WORKDIR /career-api
COPY career-api/package.json ./
RUN npm install --prefer-offline
COPY career-api/ .

EXPOSE 4000
CMD ["node", "server.mjs"]
