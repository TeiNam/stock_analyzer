# modules/data_loader.py
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import pytz
from modules.mysql_connector import MySQLConnector
from utils.config import Config
from utils.logger import setup_logger
from utils.constants import TIME_PERIODS

logger = setup_logger(__name__)
config = Config.get_instance()


class NewsDataLoader:
    def __init__(self, mysql_connector: MySQLConnector):
        self.mysql_connector = mysql_connector
        self.kst = pytz.timezone('Asia/Seoul')

    def get_news_by_period(self, current_time: datetime) -> Optional[Dict[str, Any]]:
        target_time = current_time.time()  # datetime.time 객체
        target_date = current_time.date()

        # 현재 실행 시간에 맞는 기간 찾기
        selected_period = None
        for period_name, period_info in TIME_PERIODS.items():
            check_time = datetime.strptime(period_info['check_time'], "%H:%M").time()

            # 현재 시간과 체크 시간의 차이를 분으로 계산
            current_minutes = target_time.hour * 60 + target_time.minute
            check_minutes = check_time.hour * 60 + check_time.minute
            time_diff = abs(current_minutes - check_minutes)

            if time_diff <= 5:  # 5분 이내
                selected_period = (period_name, period_info)
                break

        if not selected_period:
            logger.info("현재 시각은 뉴스 수집 시간이 아닙니다.")
            return None

        period_name, period_info = selected_period
        start_time = period_info['start']
        end_time = period_info['end']

        if period_name == "MORNING":
            # 전날 14:30 ~ 오늘 08:00
            query = """
            SELECT news_id, title, section, link, pub_time
            FROM news
            WHERE (pub_date = %s AND pub_time >= %s)
               OR (pub_date = %s AND pub_time <= %s)
            ORDER BY pub_date, pub_time
            """
            prev_date = target_date - timedelta(days=1)
            params = (
                prev_date.strftime('%Y-%m-%d'), start_time,
                target_date.strftime('%Y-%m-%d'), end_time
            )
            period_str = f"{prev_date.strftime('%Y-%m-%d')} {start_time} ~ {target_date.strftime('%Y-%m-%d')} {end_time}"
        else:
            # 08:00 ~ 14:30
            query = """
            SELECT news_id, title, section, link, pub_time
            FROM news
            WHERE pub_date = %s 
              AND pub_time BETWEEN %s AND %s
            ORDER BY pub_time
            """
            params = (
                target_date.strftime('%Y-%m-%d'),
                start_time,
                end_time
            )
            period_str = f"{target_date.strftime('%Y-%m-%d')} {start_time} ~ {end_time}"

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