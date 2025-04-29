import os
import shutil
import logging
from datetime import datetime

# =============================================
# 설정값
# =============================================
SOURCE_DIR = "source_files"
TARGET_DIR = "filtered_files"
KEYWORDS = ["영수증", "결제"]
LOG_DIR = "logs"

# =============================================
# 로깅 설정
# =============================================
def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(LOG_DIR, f"filter_move_log_{today}.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.getLogger().addHandler(logging.StreamHandler())

# =============================================
# 파일 이동 함수
# =============================================
def move_files_by_keyword(source_dir, target_dir, keywords):
    try:
        if not os.path.exists(source_dir):
            logging.error(f"[중단] 소스 폴더가 존재하지 않습니다: {source_dir}")
            return

        files = [f for f in os.listdir(source_dir) if f.endswith('.txt')]
        if not files:
            logging.warning(f"[경고] 소스 폴더에 텍스트 파일이 없습니다: {source_dir}")
            return

        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            file_path = os.path.join(source_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if any(keyword in content for keyword in keywords):
                    shutil.move(file_path, os.path.join(target_dir, file))
                    logging.info(f"[이동] 키워드 발견 → 파일 이동 완료: {file}")
                else:
                    logging.info(f"[스킵] 키워드 미발견 → 파일 유지: {file}")

            except Exception as e:
                logging.error(f"[실패] 파일 처리 중 오류 발생: {file} - {e}")

    except Exception as e:
        logging.exception(f"[예외] 전체 프로세스 중 오류 발생: {e}")

# =============================================
# 메인 함수
# =============================================
def main():
    setup_logger()
    move_files_by_keyword(SOURCE_DIR, TARGET_DIR, KEYWORDS)

if __name__ == "__main__":
    main()
