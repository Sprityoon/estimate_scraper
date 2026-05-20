# 1단계: 프론트엔드 빌드 (Node.js)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 2단계: 실행 환경 구성 (Python)
FROM python:3.11-slim
WORKDIR /app

# 시스템 의존성 설치 (Playwright/Scrapling 실행용)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requests pandas openpyxl flask flask-cors scrapling curl-cffi playwright browserforge parsel w3lib lxml
RUN python -m playwright install chromium --with-deps

# 빌드된 프론트엔드 파일 복사
COPY --from=builder /app/out ./static

# 백엔드 소스 복사
COPY server.py update_legal_dong.py ./

# 실행 (Port 5000)
EXPOSE 5000
CMD ["python", "server.py"]
