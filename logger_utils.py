# logger_utils.py
import logging
from datetime import datetime
import os

def setup_logger(name, log_dir='./logs'):
    """모듈별 로그 파일 생성 (날짜, 시간 포함)"""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_filename = f"{name}_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 중복 핸들러 방지
    if not logger.handlers:
        fh = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)

    return logger