import os
from utils import setup_logger, ensure_dir
from preprocessing import preprocess_folder
from azure_client import AzureReceiptClient
from postprocessing import load_lookup_table, process_folder

# =============================================
# 폴더 및 파일 경로 설정
# =============================================
INPUT_IMAGE_DIR = './input_images'
PROCESSED_IMAGE_DIR = './processed_images'
AZURE_RESULT_DIR = './results/json'
CSV_OUTPUT_PATH = './results/csv/final_output.csv'
LOOKUP_TABLE_PATH = './lookup_table.csv'
LOG_DIR = './logs'

# =============================================
# 로깅 설정
# =============================================
logger = setup_logger('run_pipeline', log_dir=LOG_DIR)

# =============================================
# 전체 파이프라인 실행
# =============================================
def run_pipeline():
    try:
        logger.info("🚀 영수증 처리 파이프라인 시작")

        # Step 1: 이미지 전처리
        logger.info("📌 Step 1: 이미지 전처리 시작")
        ensure_dir(PROCESSED_IMAGE_DIR, logger)
        preprocess_folder(INPUT_IMAGE_DIR, PROCESSED_IMAGE_DIR)
        logger.info("✅ Step 1: 이미지 전처리 완료")

        # Step 2: Azure OCR 분석
        logger.info("📌 Step 2: Azure OCR 분석 시작")
        ensure_dir(AZURE_RESULT_DIR, logger)
        client = AzureReceiptClient()
        client.analyze_folder(PROCESSED_IMAGE_DIR, AZURE_RESULT_DIR)
        logger.info("✅ Step 2: Azure OCR 분석 완료")

        # Step 3: 결과 후처리 및 CSV 저장
        logger.info("📌 Step 3: 후처리 및 CSV 생성 시작")
        output_dir = os.path.dirname(CSV_OUTPUT_PATH) or '.'
        ensure_dir(output_dir, logger)
        lookup_table = load_lookup_table(LOOKUP_TABLE_PATH)
        process_folder(AZURE_RESULT_DIR, CSV_OUTPUT_PATH, lookup_table)
        logger.info("✅ Step 3: 후처리 및 CSV 생성 완료")

        logger.info("🎉 전체 파이프라인 성공적으로 완료되었습니다.")

    except Exception as e:
        logger.exception(f"❌ 파이프라인 실행 중 예외 발생: {e}")

# =============================================
# 메인 진입점
# =============================================
if __name__ == "__main__":
    run_pipeline()
