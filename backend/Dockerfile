FROM python:3.11-slim

WORKDIR /app

# 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    libpq-dev \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright chromium 설치 (커뮤니티 딜 실시간 가격 크롤링용)
RUN python -m playwright install chromium --with-deps

# 소스 복사
COPY . .

# 쉘 변수 확장 문제 우회 - Python으로 직접 포트 읽기
CMD ["python", "-c", "import os,uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8001)))"]
