import logging
import sys
import traceback
from pathlib import Path

# 공통 설정
script_path = Path(__file__).resolve()
app_path = ""
for parent in script_path.parents:
    if parent.name in ("idp", "DEX", "PEX"):
        app_path = str(parent)
        break

if not app_path:
    raise FileNotFoundError("idp, DEX, PEX not found in path")

if app_path not in sys.path:
    sys.path.append(app_path)

from util import idp_utils
from your_module import (
    convert_image_folder_to_png,
    run_yolo_crop_on_folder,
    analyze_cropped_images_with_azure,
    postprocess_receipt_json
)

LOGGER_NAME = ""
LOG_LEVEL = logging.DEBUG
logger = idp_utils.setup_logger(LOGGER_NAME, LOG_LEVEL)


def run_receipt_ocr_pipeline(in_params: dict) -> str:
    """
    전체 OCR 파이프라인 실행
    1) URL 다운로드
    2) PNG 변환
    3) YOLO 크롭
    4) Azure 분석
    5) 후처리
    """
    try:
        # 1. URL 다운로드
        logger.info("Step 1: 다운로드 시작")
        downloaded = idp_utils.download_file_url(in_params)
        logger.info(f"다운로드 완료: {downloaded}")

        # 2. PNG 변환
        logger.info("Step 2: PNG 변환")
        in_params["original_image_path"] = in_params["original_image_path"]  # 폴더 기준
        in_params["preprocessing_image_path"] = in_params["preprocessing_image_path"]
        convert_image_folder_to_png(in_params)

        # 3. YOLO 크롭
        logger.info("Step 3: YOLO 크롭")
        run_yolo_crop_on_folder(in_params)

        # 4. Azure 분석
        logger.info("Step 4: Azure 분석")
        analyze_cropped_images_with_azure(in_params)

        # 5. 후처리
        logger.info("Step 5: 후처리")
        postprocess_receipt_json({
            "input_json_folder": in_params["result_json_path"],
            "output_json_folder": in_params["final_output_json_path"]
        })

        return "전체 프로세스 완료"

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# ─ 테스트 ─
if __name__ == "__main__":
    test_params = {
        "downloadURL": "https://your-bucket/sample1.jpg",
        "savePath": "sample_input/sample1.jpg",
        "original_image_path": "sample_input",               # 원본 이미지 폴더
        "preprocessing_image_path": "sample_output",         # PNG 저장 폴더
        "cropped_image_path": "cropped_output",              # YOLO 결과
        "result_json_path": "result_output",                 # Azure 결과
        "final_output_json_path": "processed_output",        # 최종 후처리
        "yolo_model_path": "best.pt",
        "azure_endpoint": "https://<your-resource>.cognitiveservices.azure.com",
        "azure_key": "<your-key>"
    }

    result = run_receipt_ocr_pipeline(test_params)
    print(result)