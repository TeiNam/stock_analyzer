# utils/config.py
import os
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    _instance = None

    @staticmethod
    def get_instance():
        if Config._instance is None:
            Config._instance = Config()
        return Config._instance

    def __init__(self):
        # .env 파일 로드
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
                'api_key': os.getenv('CLAUDE_API_KEY'),
                'model': "claude-3-sonnet-20240229",
                'max_tokens': 4000
            },
            'slack': {
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL')
            },
            'retry': {
                'max_retries': int(os.getenv('MAX_RETRIES', 3)),
                'retry_delay': int(os.getenv('RETRY_DELAY', 5))
            }
        }

        # 필수 설정값 검증
        required_envs = [
            ('DB_HOST', config['db']['host']),
            ('DB_USER', config['db']['user']),
            ('DB_PASSWORD', config['db']['password']),
            ('DB_NAME', config['db']['database']),
            ('CLAUDE_API_KEY', config['claude']['api_key']),
            ('SLACK_WEBHOOK_URL', config['slack']['webhook_url'])
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