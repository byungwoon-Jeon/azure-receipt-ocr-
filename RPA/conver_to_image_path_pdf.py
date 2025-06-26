import logging
import sys
import os
import traceback
from pathlib import Path
from PIL import Image

# ─ 공통 세팅 ─
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


def convert_image_folder_to_png(in_params: dict) -> str:
    """
    폴더 내의 이미지 파일 하나를 PNG로 변환하여 저장

    Args:
        in_params (dict): {
            "original_image_path": 원본 이미지가 들어 있는 폴더 경로,
            "preprocessing_image_path": PNG 파일을 저장할 폴더 경로
        }

    Returns:
        str: 변환된 PNG 파일 경로
    """
    try:
        input_dir = Path(in_params["original_image_path"])
        output_dir = Path(in_params["preprocessing_image_path"])
        output_dir.mkdir(parents=True, exist_ok=True)

        # 입력 폴더에서 이미지 파일 하나 찾기 (확장자 제한)
        supported_exts = (".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".png")
        candidates = [f for f in input_dir.iterdir() if f.suffix.lower() in supported_exts]

        if not candidates:
            raise FileNotFoundError(f"지원되는 이미지 파일이 없습니다: {input_dir}")

        input_file = candidates[0]
        output_file = output_dir / (input_file.stem + ".png")

        with Image.open(input_file) as img:
            if img.mode in ("RGBA", "P", "L"):
                img = img.convert("RGB")
            img.save(output_file, format="PNG")

        logger.info(f"이미지 PNG 변환 완료: {output_file}")
        return str(output_file)

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# ─ 테스트 ─
if __name__ == "__main__":
    test_params = {
        "original_image_path": "sample_input",             # 이미지가 들어있는 폴더
        "preprocessing_image_path": "sample_output"        # 변환된 PNG 저장할 폴더
    }
    result = convert_image_folder_to_png(test_params)
    print("변환 결과:", result)