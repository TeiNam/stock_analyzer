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
        try:
            now = datetime.now(self.kst)
            logger.info(f"현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            # DB에서 뉴스 조회
            news_data = self.data_loader.get_news_by_period(now)

            if not news_data or not news_data['news_list']:
                logger.warning("조회된 뉴스가 없습니다")
                return None

            logger.info(f"뉴스 {len(news_data['news_list'])}건에 대해 분석을 시작합니다.")

            # Claude를 통한 뉴스 분석
            analyzed_result = self.claude_client.analyze_news(news_data['news_list'])

            if not analyzed_result or not analyzed_result['news_items']:
                logger.warning("분석된 뉴스가 없습니다")
                return None

            result = {
                'date': news_data['date'],
                'period': news_data['period'],
                'total_count': news_data['total_count'],
                'selected_count': len(analyzed_result['news_items']),
                'news_items': analyzed_result['news_items'],
                'market_analysis': analyzed_result.get('market_analysis', []),
                'usage_info': analyzed_result.get('usage_info', {})
            }

            logger.info(f"뉴스 분석 완료: 전체 {result['total_count']}건 중 {result['selected_count']}건 선택")
            return result

        except Exception as e:
            logger.error(f"뉴스 분석 중 오류 발생: {str(e)}", exc_info=True)
            return None