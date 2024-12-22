#!/bin/bash
# docker/entrypoint.sh

# 로그 디렉토리 생성
mkdir -p /app/logs

# 메인 스크립트 실행
exec python /app/main.py