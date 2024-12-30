# docker/Dockerfile
FROM --platform=linux/amd64 python:3.12.8-slim

# 타임존 설정
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 작업 디렉토리 생성
WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 타임존 설정
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 파일 복사
COPY requirements.txt .
COPY . .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 실행 권한 부여
RUN chmod +x /app/docker/entrypoint.sh

# 실행
ENTRYPOINT ["/app/docker/entrypoint.sh"]