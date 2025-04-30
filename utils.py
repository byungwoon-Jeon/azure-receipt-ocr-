import os
import json
import logging
from datetime import datetime, date, time

# 로깅 유틸
def setup_logger(name, log_dir = './logs', level=logging.INFO):
    """
    모듈별 로거 생성 함수
    
    Args:
        name (str): 로거 이름
        log_dir (str): 로그 파일 저장 경로
        level (int): 로그 레벨(기본값 : logging.INFO)
    
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_filename = f"{name}_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    
    return logger

# 공통 유틸 함수

def ensure_dir(path, logger=None):
    # 디렉토리가 없을 경우 생성
    if not os.path.exists(path):
        os.makedirs(path)
        if logger:
            logger.info(f"Created directory: {path}")

def is_image_file(filename):
    # 이미지 확장자 판별
    return filename.lower().endswith(('.jpg', '.jpeg', '.png'))

def save_json(data, path, logger=None):
    """JSON 파일로 저장 및 datetime 자동 변환"""
    def convert(obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    with open(path, 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=convert)
        if logger:
            logger.info(f"Saved JSON: {path}")

def load_json(path, logger=None):
    """JSON 파일 불러오기"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if logger:
            logger.info(f"Loaded JSON: {path}")
        return data
    except Exception as e:
        if logger:
            logger.error(f"[에러] JSON 로딩 실패 : {path} : {e}")
        return None