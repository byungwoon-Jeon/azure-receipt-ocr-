import os
import pandas as pd
from datetime import datetime
import logging

# =============================================
# 설정값 (운영팀이 수정해야 할 수도 있음)
# =============================================
SOURCE_DIR = "D:\Azure_Prebuilt_Receipt\example_excels"  # 소스 엑셀 폴더 경로
OUTPUT_DIR = "D:\Azure_Prebuilt_Receipt\output"          # 결과 저장 폴더 경로
LOG_DIR = "D:\Azure_Prebuilt_Receipt\logs"               # 로그 저장 폴더 경로

# =============================================
# 로깅 설정
# =============================================
def setup_logger():
    """로그 파일과 콘솔에 로깅 설정을 초기화합니다."""
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(LOG_DIR, f"merge_excel_{today}.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

# =============================================
# 엑셀 병합 기능
# =============================================
def merge_excels(source_dir, output_dir):
    """
    주어진 폴더의 모든 엑셀 파일을 하나로 병합하고 저장합니다.
    
    Args:
        source_dir (str): 원본 엑셀 파일들이 위치한 폴더
        output_dir (str): 병합된 결과를 저장할 폴더
    """
    try:
        # 소스 폴더 존재 확인
        if not os.path.exists(source_dir):
            logging.error(f"[중단] 소스 폴더가 존재하지 않습니다: {source_dir}")
            return

        # 소스 폴더 내 .xlsx 파일 리스트업
        files = [f for f in os.listdir(source_dir) if f.endswith('.xlsx')]
        if not files:
            logging.warning(f"[경고] 소스 폴더에 엑셀 파일이 없습니다: {source_dir}")
            return

        dataframes = []

        for file in files:
            filepath = os.path.join(source_dir, file)
            try:
                df = pd.read_excel(filepath)
                dataframes.append(df)
                logging.info(f"[성공] 엑셀 파일 로드 완료: {file}")
            except Exception as e:
                logging.error(f"[실패] 엑셀 파일 읽기 실패: {file} - {e}")

        # 파일들이 하나라도 성공적으로 읽혔는지 확인
        if not dataframes:
            logging.warning("[경고] 읽을 수 있는 엑셀 파일이 없습니다. 병합 중단.")
            return

        # 데이터 병합
        merged_df = pd.concat(dataframes, ignore_index=True)
        logging.info(f"[진행] 총 {len(dataframes)}개 파일 병합 완료.")

        # 결과 저장
        os.makedirs(output_dir, exist_ok=True)
        today = datetime.now().strftime('%Y%m%d')
        output_path = os.path.join(output_dir, f"merged_{today}.xlsx")

        merged_df.to_excel(output_path, index=False)
        logging.info(f"[완료] 병합 파일 저장 완료: {output_path}")

    except Exception as e:
        logging.exception(f"[예외] 예기치 않은 오류 발생: {e}")

# =============================================
# 메인 함수
# =============================================
def main():
    """프로그램 실행 진입점."""
    setup_logger()
    merge_excels(SOURCE_DIR, OUTPUT_DIR)

if __name__ == "__main__":
    main()