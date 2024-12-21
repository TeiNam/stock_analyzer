# modules/slack_sender.py
import requests
from typing import Dict
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)
config = Config.get_instance()

class SlackSender:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.max_retries = config.get('retry.max_retries', 3)
        self.retry_delay = config.get('retry.retry_delay', 5)

    def send_news_summary(self, analysis_result: Dict):
        """분석된 뉴스 요약을 슬랙 웹훅으로 전송"""

        # 헤더 메시지 구성
        header_text = f"📰 {analysis_result['date']} {analysis_result['period']} 주요 뉴스 {analysis_result['selected_count']}건"

        try:
            # 헤더 메시지 전송
            requests.post(self.webhook_url, json={
                'text': header_text
            })

            # 뉴스 항목들을 중요도 순으로 정렬
            sorted_news = sorted(
                analysis_result['news_items'],
                key=lambda x: x['importance'],
                reverse=True
            )

            # 뉴스 목록 메시지 구성
            message = ""
            for idx, news in enumerate(sorted_news, 1):
                message += f"{idx}. <{news['link']}|{news['title']}>\n"

                # 20개씩 끊어서 메시지 전송 (슬랙 메시지 길이 제한 고려)
                if idx % 20 == 0 or idx == len(sorted_news):
                    requests.post(self.webhook_url, json={
                        'text': message,
                        'unfurl_links': False  # 링크 미리보기 비활성화
                    })
                    message = ""

            logger.info(f"슬랙 메시지 전송 완료: {len(sorted_news)}개 뉴스")
            return True

        except Exception as e:
            logger.error(f"슬랙 메시지 전송 오류: {str(e)}")
            return False