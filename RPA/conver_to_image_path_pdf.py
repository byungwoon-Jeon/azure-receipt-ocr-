import logging
import sys
import os
import traceback
from pathlib import Path
from PIL import Image  # PIL 사용

# 경로 설정
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

LOGGER_NAME = ""
LOG_LEVEL = logging.DEBUG
logger = idp_utils.setup_logger(LOGGER_NAME, LOG_LEVEL)


def convert_image_to_png(in_params: dict) -> str:
    """
    다운로드된 이미지 파일을 PNG로 변환하여 저장
    Args:
        in_params (dict): {
            "original_image_path": 원본 이미지 경로,
            "preprocessing_image_path": 변환 이미지 저장 경로
        }

    Returns:
        str: 저장된 PNG 파일 경로
    """
    try:
        input_path = in_params["original_image_path"]
        output_path = in_params["preprocessing_image_path"]

        # 이미지 열기
        with Image.open(input_path) as img:
            # RGBA 혹은 RGB로 변환 (에러 방지)
            if img.mode in ("RGBA", "P", "L"):
                img = img.convert("RGB")
            img.save(output_path, format="PNG")

        logger.info(f"이미지 PNG 변환 완료: {output_path}")
        return output_path

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# 단독 테스트용
if __name__ == "__main__":
    test_params = {
        "original_image_path": "sample_input/image1.jpg",
        "preprocessing_image_path": "sample_output/image1_converted.png"
    }
    result = convert_image_to_png(test_params)
    print("변환 결과:", result)