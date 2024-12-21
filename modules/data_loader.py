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
        target_time = current_time.time()
        target_date = current_time.date()

        # TIME_PERIODS 상수를 사용하여 시간 구간 체크
        for period_name, period_info in TIME_PERIODS.items():
            check_time = datetime.strptime(period_info['check_time'], "%H:%M").time()
            if target_time < check_time:
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

                break
        else:
            logger.info("현재 시각은 뉴스 수집 시간이 아닙니다.")
            return None

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