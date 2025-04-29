import os
import requests
import json
import logging
from datetime import datetime

# 설정값
API_URL = "https://jsonplaceholder.typicode.com/posts"
BASE_SAVE_DIR = "response"
LOG_DIR = "logs"

# 로깅 설정
def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f("api_log_{today}.log"))
    
    logging.basicConfig(
        filename = log_file,
        level=logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    

# API 호출 및 JSON 저장
def fetch_and_save_json(api_url, save_dir):
    try:
        logging.info(f"API 호출 시작: {api_url}")
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            logging.error(f"API 호출 실패 : status={response.status_code}")
            return
        
        data = response.json()
        
        # 폴더 생성
        date_str = datetime.now().strftime('%Y%m%d')
        time_str = datetime.now().strftime('%H%M%S')
        save_path = os.path.join(save_dir, date_str)
        os.makedirs(save_path, exist_ok=True)
        
        file_path = os.path.join(save_path, f("response_{time_str}.json"))
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"응답 저장 완료 : {file_path}")
        
    except Exception as e:
        logging.exception(f"[에러] API 호출 또는 저장 중 오류 발생: {e}")
    
    def main():
        setup_logger()
        fetch_and_save_json(API_URL, BASE_SAVE_DIR)
        
    if __name__ == "__main__":
        main()