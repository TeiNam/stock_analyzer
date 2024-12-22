# main.py
import time
import logging
from utils.config import Config
from utils.logger import setup_logger
from modules.news_scheduler import NewsAnalysisScheduler
from utils.constants import TIME_PERIODS

logger = setup_logger(__name__)
config = Config.get_instance()


def main():
    try:
        logger.info("뉴스 분석 서비스 시작")
        next_times = [period['check_time'] for period in TIME_PERIODS.values()]
        logger.info(f"다음 실행 예정 시간: {', '.join(next_times)}")

        # 스케줄러 시작 (초기 실행 없이)
        scheduler = NewsAnalysisScheduler(run_immediately=False)

        try:
            scheduler.start()
            logger.info("스케줄러가 시작되었습니다.")

            # 메인 스레드는 계속 실행
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("서비스 종료 요청을 받았습니다.")
            scheduler.stop()
            scheduler.join()
            logger.info("스케줄러가 정상적으로 종료되었습니다.")

    except Exception as e:
        logger.error(f"서비스 실행 중 오류 발생: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()