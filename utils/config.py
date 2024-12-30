# utils/config.py
import os
from typing import Dict, Any
from dotenv import load_dotenv
import pytz

# Timezone 설정
KST = pytz.timezone('Asia/Seoul')

class Config:
    _instance = None

    # Claude 필수 설정 기본값
    CLAUDE_REQUIRED = {
        'api_key': None,  # 환경변수로 설정 필요
        'model': "claude-3-sonnet-20240229",
        'max_tokens': 4000,
        'max_news_items': 20
    }

    # 뉴스 분석 관련 설정
    NEWS_DEFAULTS = {
        'similarity_threshold': 70  # 기사 유사도 임계값
    }

    # 로깅 설정
    LOGGING_DEFAULTS = {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'dir': 'logs',
        'file_format': 'news_analyzer_{}.log',
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 30
    }

    @staticmethod
    def get_instance():
        if Config._instance is None:
            Config._instance = Config()
        return Config._instance

    def __init__(self):
        load_dotenv()
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """환경변수에서 설정 로드"""
        config = {
            'db': {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT', 3306)),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'database': os.getenv('DB_NAME')
            },
            'claude': {
                'api_key': os.getenv('CLAUDE_API_KEY', self.CLAUDE_REQUIRED['api_key']),
                'model': os.getenv('CLAUDE_MODEL', self.CLAUDE_REQUIRED['model']),
                'max_tokens': int(os.getenv('CLAUDE_MAX_TOKENS', self.CLAUDE_REQUIRED['max_tokens'])),
                'max_news_items': int(os.getenv('MAX_NEWS_ITEMS', self.CLAUDE_REQUIRED['max_news_items']))
            },
            'slack': {
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL')
            },
            'news': self.NEWS_DEFAULTS,
            'logging': self.LOGGING_DEFAULTS
        }

        # 필수 환경변수 검증
        required_envs = [
            ('DB_HOST', config['db']['host']),
            ('DB_USER', config['db']['user']),
            ('DB_PASSWORD', config['db']['password']),
            ('DB_NAME', config['db']['database']),
            ('SLACK_WEBHOOK_URL', config['slack']['webhook_url']),
            ('CLAUDE_API_KEY', config['claude']['api_key'])
        ]

        missing_envs = [env[0] for env in required_envs if not env[1]]
        if missing_envs:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_envs)}")

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value