# modules/news_analyzer.py
from datetime import datetime
import pytz
from typing import Dict, Optional
from modules.claude_client import ClaudeClient
from modules.data_loader import NewsDataLoader
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)
config = Config.get_instance()

class NewsAnalyzer:
    def __init__(self, data_loader: NewsDataLoader, claude_api_key: str):
        self.data_loader = data_loader
        self.claude_client = ClaudeClient(claude_api_key)
        self.kst = pytz.timezone('Asia/Seoul')

    def analyze_news_by_period(self) -> Optional[Dict]:
        """현재 시간 기준으로 구간별 뉴스 분석"""
        now = datetime.now(self.kst)

        # DB에서 뉴스 조회
        news_data = self.data_loader.get_news_by_period(now)

        if not news_data or not news_data['news_list']:
            return None

        # Claude를 통한 뉴스 분석
        analyzed_news = self.claude_client.analyze_news(news_data['news_list'])

        return {
            'date': news_data['date'],
            'period': news_data['period'],
            'total_count': news_data['total_count'],
            'selected_count': len(analyzed_news),
            'news_items': analyzed_news
        }