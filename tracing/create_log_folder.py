import os
import logging
from datetime import datetime

# =============================================
# 설정값
# =============================================
BASE_LOG_DIR = "logs"  # 최상위 로그 디렉토리

# =============================================
# 로깅 설정 함수
# =============================================
def setup_daily_logger(base_log_dir):
    """
    오늘 날짜 기준으로 로그 폴더를 생성하고 log.txt 파일에 기록하는 로깅 설정 함수.
    """
    try:
        # 오늘 날짜 폴더 생성
        today_str = datetime.now().strftime('%Y%m%d')
        log_dir = os.path.join(base_log_dir, today_str)
        os.makedirs(log_dir, exist_ok=True)

        # 로그 파일 경로
        log_file_path = os.path.join(log_dir, "log.txt")

        # 로깅 설정
        logging.basicConfig(
            filename=log_file_path,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

        # 콘솔 출력도 추가
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

        logging.info("✅ 로그 디렉토리 및 파일 설정 완료")

    except Exception as e:
        print(f"[에러] 로깅 설정 실패: {e}")

# =============================================
# 메인 로직
# =============================================
def main():
    try:
        setup_daily_logger(BASE_LOG_DIR)
        logging.info("🚀 프로그램 시작")
        # 여기서 필요한 다른 로직이 있다면 넣을 수 있음
        logging.info("✅ 작업 완료")
    except Exception as e:
        logging.exception(f"[예외] 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()