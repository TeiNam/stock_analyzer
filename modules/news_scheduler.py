# modules/news_scheduler.py
import schedule
import time
import threading
from datetime import datetime
from modules.mysql_connector import MySQLConnector
from modules.news_analyzer import NewsAnalyzer
from modules.slack_sender import SlackSender
from modules.data_loader import NewsDataLoader
from utils.config import Config
from utils.logger import setup_logger
from utils.constants import TIME_PERIODS, KST

logger = setup_logger(__name__)
config = Config.get_instance()

class NewsAnalysisScheduler(threading.Thread):
    def __init__(self, run_immediately: bool = False):
        super().__init__()
        self.schedule_times = [period['check_time'] for period in TIME_PERIODS.values()]
        self.run_immediately = run_immediately

        # DB 커넥터 및 데이터 로더 초기화
        self.db_connector = MySQLConnector()
        self.data_loader = NewsDataLoader(self.db_connector)

        # 분석기 및 슬랙 발송 객체 초기화
        self.analyzer = NewsAnalyzer(
            self.data_loader,
            config.get('claude.api_key')
        )
        self.slack_sender = SlackSender(
            config.get('slack.webhook_url')
        )

    def run(self):
        self.is_running = True

        # 스케줄 등록
        for time_str in self.schedule_times:
            schedule.every().day.at(time_str).do(self.run_analysis)
            logger.info(f"스케줄 등록: {time_str} KST")

        logger.info("뉴스 분석 스케줄러 시작됨")
        logger.info(f"실행 시간: 매일 {', '.join(self.schedule_times)} KST")

        if self.run_immediately:
            logger.info("초기 분석 시작")
            self.run_analysis()

        while self.is_running:
            schedule.run_pending()
            time.sleep(60)

    def stop(self):
        self.is_running = False

    def run_analysis(self):
        """뉴스 분석 및 발송 실행"""
        try:
            current_datetime = datetime.now(KST)
            logger.info(f"뉴스 분석 시작: {current_datetime.strftime('%Y-%m-%d %H:%M')} KST")

            analysis_result = self.analyzer.analyze_news_by_period()

            if analysis_result and analysis_result['news_items']:
                self.slack_sender.send_news_summary(analysis_result)

                logger.info(f"뉴스 분석 완료: {analysis_result['selected_count']}개 기사 발송")
                return {
                    "status": "success",
                    "analyzed_count": analysis_result['selected_count']
                }
            else:
                logger.warning("분석할 뉴스가 없습니다.")
                return {
                    "status": "warning",
                    "message": "분석할 뉴스가 없습니다."
                }

        except Exception as e:
            error_msg = f"뉴스 분석 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "message": error_msg}