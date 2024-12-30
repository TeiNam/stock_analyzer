# modules/data_loader.py
from typing import Dict, Optional, Any
from datetime import datetime
import pytz
from modules.mysql_connector import MySQLConnector
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)
config = Config.get_instance()


class NewsDataLoader:
    # 스케줄러 실행 시간별 수집 시간 범위 정의
    ANALYSIS_PERIODS = {
        "08:40": {"start": "15:00", "end": "08:30"},  # 전일 21:00 - 당일 09:00
        "15:10": {"start": "08:30", "end": "15:00"},  # 당일 12:00 - 15:00
    }

    def __init__(self, mysql_connector: MySQLConnector):
        self.mysql_connector = mysql_connector
        self.kst = pytz.timezone('Asia/Seoul')

    def get_news_by_period(self, current_time: datetime) -> Optional[Dict[str, Any]]:
        target_time = current_time.time()
        target_date = current_time.date()

        # 현재 시간과 가장 가까운 분석 시간 찾기
        current_minutes = target_time.hour * 60 + target_time.minute
        selected_period = None

        for analysis_time, period in self.ANALYSIS_PERIODS.items():
            check_time = datetime.strptime(analysis_time, "%H:%M").time()
            check_minutes = check_time.hour * 60 + check_time.minute
            time_diff = abs(current_minutes - check_minutes)

            if time_diff <= 5:  # 5분 이내
                selected_period = (analysis_time, period)
                break

        if not selected_period:
            logger.info("현재 시각은 뉴스 분석 시간이 아닙니다.")
            return None

        analysis_time, period = selected_period

        # 첫 번째 시간대(09:10)의 경우 전날 데이터도 포함
        if analysis_time == "08:40":
            query = """
            SELECT news_id, title, section, link, pub_time, create_at
            FROM news
            WHERE (
                (DATE(create_at) = DATE_SUB(%s, INTERVAL 1 DAY) AND TIME(create_at) >= %s)
                OR (DATE(create_at) = %s AND TIME(create_at) <= %s)
            )
            ORDER BY create_at
            """
            params = (
                target_date.strftime('%Y-%m-%d'),
                period['start'],
                target_date.strftime('%Y-%m-%d'),
                period['end']
            )
        else:
            # 일반적인 경우
            query = """
            SELECT news_id, title, section, link, pub_time, create_at
            FROM news
            WHERE DATE(create_at) = %s 
            AND TIME(create_at) BETWEEN %s AND %s
            ORDER BY create_at
            """
            params = (
                target_date.strftime('%Y-%m-%d'),
                period['start'],
                period['end']
            )

        period_str = f"{target_date.strftime('%Y-%m-%d')} {period['start']} ~ {period['end']}"
        logger.info(f"뉴스 조회 시작: {period_str}")

        results = self.mysql_connector.execute_query(query, params)

        if not results:
            logger.warning("조회된 뉴스가 없습니다.")
            return None

        logger.info(f"뉴스 조회 완료: {period_str}, {len(results)}건")

        return {
            'news_list': results,
            'period': period_str,
            'date': target_date.strftime('%Y-%m-%d'),
            'total_count': len(results)
        }