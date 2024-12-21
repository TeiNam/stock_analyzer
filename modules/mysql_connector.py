# modules/mysql_connector.py
import mysql.connector
from mysql.connector import Error
from typing import Optional
import time
from utils.config import Config
from utils.logger import setup_logger
from utils.constants import DB_CONFIG_KEYS

logger = setup_logger(__name__)
config = Config.get_instance()

class MySQLConnector:
    def __init__(self):
        self.config = {key: config.get(f'db.{key}') for key in DB_CONFIG_KEYS}
        self._connection = None
        self.max_retries = config.get('retry.max_retries', 3)
        self.retry_delay = config.get('retry.retry_delay', 5)

    def connect(self) -> None:
        """데이터베이스 연결 (재시도 로직 포함)"""
        retries = 0
        last_exception = None

        while retries < self.max_retries:
            try:
                if not self._connection or not self._connection.is_connected():
                    self._connection = mysql.connector.connect(**self.config)
                    logger.info("MySQL 데이터베이스 연결 성공")
                return
            except Error as e:
                last_exception = e
                retries += 1
                if retries < self.max_retries:
                    wait_time = self.retry_delay * retries
                    logger.warning(f"MySQL 연결 실패 ({retries}/{self.max_retries}), "
                                   f"{wait_time}초 후 재시도... 오류: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"MySQL 연결 최대 재시도 횟수 초과: {str(e)}")

        raise last_exception

    def disconnect(self) -> None:
        """데이터베이스 연결 해제"""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            logger.info("MySQL 데이터베이스 연결 해제")

    def execute_with_retry(self, operation: callable):
        """재시도 로직을 포함한 데이터베이스 작업 실행"""
        retries = 0
        last_exception = None

        while retries < self.max_retries:
            try:
                return operation()
            except Error as e:
                last_exception = e
                retries += 1
                if retries < self.max_retries:
                    wait_time = self.retry_delay * retries
                    logger.warning(f"데이터베이스 작업 실패 ({retries}/{self.max_retries}), "
                                   f"{wait_time}초 후 재시도... 오류: {str(e)}")
                    self.disconnect()
                    time.sleep(wait_time)
                else:
                    logger.error(f"데이터베이스 작업 최대 재시도 횟수 초과: {str(e)}")

        return None

    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        """쿼리 실행 및 결과 반환"""

        def execute():
            self.connect()
            cursor = self._connection.cursor(dictionary=True)
            try:
                cursor.execute(query, params)
                return cursor.fetchall()
            finally:
                cursor.close()
                self.disconnect()

        return self.execute_with_retry(execute)