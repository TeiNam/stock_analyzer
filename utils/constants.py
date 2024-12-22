# utils/constants.py
from typing import Dict, Any
import pytz

# Timezone 설정
KST = pytz.timezone('Asia/Seoul')

# 데이터베이스 관련 상수
DB_CONFIG_KEYS = [
    'host',
    'port',
    'user',
    'password',
    'database'
]

# 시간 관련 상수
TIME_PERIODS: Dict[str, Dict[str, Any]] = {
    "MORNING": {
        "start": "14:30",  # 전일
        "end": "08:00",
        "check_time": "08:10"
    },
    "AFTERNOON": {
        "start": "08:00",
        "end": "14:30",
        "check_time": "14:40"
    }
}

# 로깅 관련 상수
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_DIR = 'logs'
LOG_FILE_FORMAT = 'news_analyzer_{}.log'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 30

# API 관련 상수
CLAUDE_MODEL = "claude-3-sonnet-20240229"
CLAUDE_MAX_TOKENS = 4000
MAX_NEWS_ITEMS = 30