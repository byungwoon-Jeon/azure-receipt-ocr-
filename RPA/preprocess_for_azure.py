import os
import cv2
import logging
from pathlib import Path
from util import idp_utils

def preprocess_image_for_azure(in_params: dict) -> dict:
    """
    Azure OCR 모델에 맞게 이미지를 리사이즈하고 PNG 형식으로 저장하는 전처리 함수

    Args:
        in_params (dict): {
            "image_path": str,
            "save_dir": str,
            "python_log_file_path": str (optional)
        }

    Returns:
        dict: {
            "success": True, "saved_path": str
        } or {
            "success": False, "error": str
        }
    """

    # === Logger 설정 ===
    logger_name = "das_ccr_azure_pre_processing"
    log_level = logging.DEBUG
    if "python_log_file_path" in in_params:
        logger = idp_utils.setup_logger(logger_name, log_level, in_params["python_log_file_path"])
    else:
        logger = idp_utils.setup_logger(logger_name, log_level)

    try:
        image_path = in_params["image_path"]
        save_dir = in_params["save_dir"]

        # === 이미지 읽기 ===
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"이미지를 불러올 수 없습니다: {image_path}")

        h, w = img.shape[:2]
        logger.debug(f"Original image size: {w}x{h}")

        # === Azure OCR 해상도 제한 적용 ===
        max_size = 10000
        min_size = 50

        scale_w = min(max_size / w, 1.0) if w > max_size else max(min_size / w, 1.0) if w < min_size else 1.0
        scale_h = min(max_size / h, 1.0) if h > max_size else max(min_size / h, 1.0) if h < min_size else 1.0
        scale = min(scale_w, scale_h)

        if scale != 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.debug(f"Resized image to: {new_w}x{new_h}")
        else:
            logger.debug("No resizing needed.")

        # === 저장 경로 설정 ===
        os.makedirs(save_dir, exist_ok=True)
        filename = Path(image_path).stem + ".png"
        save_path = os.path.join(save_dir, filename)

        # === 이미지 저장 ===
        success = cv2.imwrite(save_path, img)
        if not success:
            raise IOError(f"이미지 저장 실패: {save_path}")

        logger.info(f"Preprocessed image saved to: {save_path}")
        return {"success": True, "saved_path": save_path}

    except Exception as e:
        logger.error(f"전처리 중 오류 발생: {e}")
        return {"success": False, "error": str(e)}


# =========================
# 테스트용 메인 실행 코드
# =========================
if __name__ == "__main__":
    test_input = {
        "image_path": "./test_images/sample_receipt.jpg",
        "save_dir": "./test_output/preprocessed",
        "python_log_file_path": "./test_output/preprocess_log.txt"
    }

    result = preprocess_image_for_azure(test_input)
    print("=== 테스트 결과 ===")
    print(result)