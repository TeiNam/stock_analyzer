# utils/logger.py
import logging
import logging.handlers
import os
from datetime import datetime
import pytz


def setup_logger(name: str = None) -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name if name else __name__)

    if not logger.handlers:  # 핸들러가 없을 경우에만 추가
        logger.setLevel(logging.INFO)

        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        kst = pytz.timezone('Asia/Seoul')
        current_date = datetime.now(kst).strftime('%Y-%m-%d')
        file_handler = logging.handlers.RotatingFileHandler(
            filename=f'{log_dir}/news_analyzer_{current_date}.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=30
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger