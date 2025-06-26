import logging
import sys
import os
import traceback
from pathlib import Path
from PIL import Image

from ultralytics import YOLO

# ─ 공통 설정 ─
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


def run_yolo_crop_on_folder(in_params: dict) -> str:
    """
    폴더 내 이미지들에 대해 YOLO 모델로 객체 감지 후 크롭된 이미지를 저장

    Args:
        in_params (dict): {
            "preprocessing_image_path": 전처리 이미지 폴더,
            "cropped_image_path": 크롭 이미지 저장 폴더,
            "yolo_model_path": YOLO 모델 pt 경로
        }

    Returns:
        str: 크롭 이미지 저장 폴더 경로
    """
    try:
        input_dir = Path(in_params["preprocessing_image_path"])
        output_dir = Path(in_params["cropped_image_path"])
        model_path = in_params["yolo_model_path"]
        output_dir.mkdir(parents=True, exist_ok=True)

        model = YOLO(model_path)

        images = sorted([f for f in input_dir.iterdir() if f.suffix.lower() == ".png"])
        if not images:
            raise FileNotFoundError("PNG 이미지가 없습니다.")

        for img_path in images:
            results = model(str(img_path))
            boxes = results[0].boxes

            if boxes is None or len(boxes) == 0:
                logger.warning(f"디텍션 없음: {img_path}")
                continue

            image = Image.open(img_path)

            for i, box in enumerate(boxes):
                coords = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = map(int, coords)
                cropped = image.crop((x1, y1, x2, y2))

                save_path = output_dir / f"{img_path.stem}_{i}.png"
                cropped.save(save_path)
                logger.info(f"크롭 저장: {save_path}")

        return str(output_dir)

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# ─ 테스트 ─
if __name__ == "__main__":
    test_params = {
        "preprocessing_image_path": "sample_output",          # PNG 변환 이미지가 있는 폴더
        "cropped_image_path": "cropped_output",               # 결과 저장 폴더
        "yolo_model_path": "best.pt"                          # YOLO 모델 파일
    }

    result = run_yolo_crop_on_folder(test_params)
    print("크롭 결과:", result)