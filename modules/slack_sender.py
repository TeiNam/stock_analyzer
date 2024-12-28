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

    def format_news_message(self, analysis_result: Dict) -> str:
        news_items = analysis_result.get('news_items', [])
        market_analysis = analysis_result.get('market_analysis', [])
        usage_info = analysis_result.get('usage_info', {})

        # 섹션별로 뉴스 그룹화
        news_by_section = {}
        for news in news_items:
            section = news.get('section', '기타')
            if section not in news_by_section:
                news_by_section[section] = []
            news_by_section[section].append(news)

        # 뉴스 헤드라인 섹션 구성
        message = f"📰 주요 뉴스 헤드라인 ({len(news_items)}건)\n"
        message += "----------------------------\n"

        for section, items in news_by_section.items():
            message += f"\n[{section}]\n"
            for news in items:
                # 링크 형식으로 제목 포맷팅
                message += f"• <{news['link']}|{news['title']}>\n"

        # 시장 영향도 분석 섹션 구성
        if market_analysis:
            message += "\n\n📊 시장 영향도 분석\n"
            message += "----------------------------\n"

            for idx, analysis in enumerate(market_analysis, 1):
                impact_symbol = "🔴" if analysis['impact'] == "Negative" else "🟢" if analysis[
                                                                                        'impact'] == "Positive" else "⚪"
                message += f"\n{idx}. {analysis['topic']} {impact_symbol}\n"
                message += f"• 영향: {analysis['impact']} ({analysis['score']})\n"
                message += f"• 영향권: {', '.join(analysis['affected_sectors'])}\n"
                message += f"• 지속기간: {analysis['duration']}\n"
                message += f"• 분석: {analysis['analysis']}\n"

        # API 사용 정보 추가
        if usage_info:
            message += "\n\n⚙️ API 사용 정보\n"
            message += "----------------------------\n"
            message += f"• 토큰 사용량: {usage_info.get('total_tokens', 0):,} tokens "
            message += f"(입력: {usage_info.get('input_tokens', 0):,}, "
            message += f"출력: {usage_info.get('output_tokens', 0):,})\n"
            message += f"• API 호출 시간: {usage_info.get('api_time', 0):.1f}초\n"
            message += f"• API 사용 비용: ${usage_info.get('cost_usd', 0):.4f}\n"

        return message

    def split_message(self, message: str, max_length: int = 3000) -> list:
        """긴 메시지를 슬랙 제한에 맞게 분할"""
        if len(message) <= max_length:
            return [message]

        parts = []
        while message:
            if len(message) <= max_length:
                parts.append(message)
                break

            # 최대 길이에서 가장 가까운 줄바꿈 위치 찾기
            split_index = message.rfind('\n', 0, max_length)
            if split_index == -1:
                split_index = max_length

            parts.append(message[:split_index])
            message = message[split_index:].lstrip()

        return parts

    def send_news_summary(self, analysis_result: Dict):
        """분석된 뉴스 요약을 슬랙 웹훅으로 전송"""
        try:
            # 전체 메시지 포매팅
            message = self.format_news_message(analysis_result)

            # 메시지 분할 및 전송
            message_parts = self.split_message(message)
            for part in message_parts:
                requests.post(self.webhook_url, json={
                    'text': part,
                    'unfurl_links': False  # 링크 미리보기 비활성화
                })

            logger.info(f"슬랙 메시지 전송 완료: {len(analysis_result.get('news_items', []))}개 뉴스")
            return True

        except Exception as e:
            logger.error(f"슬랙 메시지 전송 오류: {str(e)}")
            return False