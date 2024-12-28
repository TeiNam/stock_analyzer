```markdown
# Stock Analytics Service

주식 시장 뉴스를 자동으로 수집하고 분석하여 중요한 뉴스를 선별해 Slack으로 전송하는 서비스입니다.

## 주요 기능

- 정해진 시간(오전 8:10, 오후 14:40)에 주기적으로 뉴스 분석
- Claude AI를 활용한 뉴스 중요도 분석
- 중복 뉴스 필터링 및 클러스터링
- 선별된 중요 뉴스를 Slack으로 자동 전송

## 시스템 요구사항

- Python 3.12+
- MySQL 데이터베이스
- Docker (선택사항)

## 설치 방법

1. 저장소 클론
```bash
git clone [repository_url]
cd stock_analytics
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
`.env` 파일을 생성하고 다음 환경변수들을 설정하세요:

```env
DB_HOST=your_db_host
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
CLAUDE_API_KEY=your_claude_api_key
SLACK_WEBHOOK_URL=your_slack_webhook_url
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_MAX_TOKENS=4000
MAX_NEWS_ITEMS=15
```

## 실행 방법

### 일반 실행
```bash
python main.py
```

### Docker 실행
```bash
docker-compose -f docker/docker-compose.yml up -d
```

## 프로젝트 구조

```
stock_analytics/
├── logs/               # 로그 파일 저장 디렉토리
├── modules/            # 핵심 기능 모듈
│   ├── claude_client.py    # Claude AI API 클라이언트
│   ├── data_loader.py      # 뉴스 데이터 로딩
│   ├── mysql_connector.py  # MySQL 데이터베이스 연결
│   ├── news_analyzer.py    # 뉴스 분석 로직
│   ├── news_scheduler.py   # 스케줄링 관리
│   └── slack_sender.py     # Slack 메시지 전송
├── utils/              # 유틸리티 기능
│   ├── config.py          # 설정 관리
│   ├── constants.py       # 상수 정의
│   └── logger.py          # 로깅 설정
└── docker/             # Docker 관련 파일
    ├── Dockerfile
    └── docker-compose.yml
```

## 주요 모듈 설명

### news_analyzer.py
- 뉴스 데이터를 분석하고 중요도를 평가
- Claude AI를 활용한 뉴스 분석 및 선별
- 유사 뉴스 클러스터링

### news_scheduler.py
- 일일 2회(오전/오후) 정기적인 뉴스 분석 스케줄링
- 분석 결과의 Slack 전송 관리

### slack_sender.py
- 분석된 뉴스 요약을 Slack으로 전송
- 뉴스 링크 및 중요도 정보 포함

### claude_client.py
- Claude AI API 연동
- 뉴스 중요도 평가 및 분류

## 스케줄 실행 시간

- 오전 리포트: 08:10 (전일 14:30 ~ 당일 08:00 뉴스)
- 오후 리포트: 14:40 (당일 08:00 ~ 14:30 뉴스)

## 로깅

- 로그 파일은 `logs` 디렉토리에 일자별로 저장
- 로그 포맷: `news_analyzer_YYYY-MM-DD.log`
- 로그 로테이션: 10MB 단위, 최대 30개 파일 유지

## 오류 처리

- 데이터베이스 연결 실패 시 자동 재시도 (최대 3회)
- API 호출 실패 시 재시도 로직 구현
- 모든 오류는 로그에 상세히 기록

## 라이선스

[라이선스 정보 추가 필요]

## 기여 방법

[기여 방법 정보 추가 필요]
```

이 README.md는 프로젝트의 주요 기능, 설치 방법, 구조, 실행 방법 등을 포함하고 있습니다. 추가로 다음 사항들을 보완하면 좋을 것 같습니다:

1. 실제 저장소 URL
2. 라이선스 정보
3. 기여 방법
4. 테스트 실행 방법
5. 문제 해결 가이드
6. API 문서화 (필요한 경우)

필요한 경우 이러한 섹션들을 추가하거나 수정할 수 있습니다.