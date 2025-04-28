import os
import cv2
from logger_utils import setup_logger

# 로그 설정 (setup_logger 사용)
logger = setup_logger('preprocessing')

def ensure_dir(path):
    """디렉토리 없으면 생성"""
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Created directory: {path}")

def preprocess_image(input_path, output_path, target_size=(1024, 1024)):
    try:
        img = cv2.imread(input_path)
        if img is None:
            logger.warning(f"Cannot read image: {input_path}")
            return

        # 그레이스케일 변환
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 비율 유지 리사이즈
        h, w = gray.shape
        scale = min(target_size[0] / h, target_size[1] / w)
        resized = cv2.resize(gray, (int(w * scale), int(h * scale)))

        # 패딩 추가
        top = (target_size[0] - resized.shape[0]) // 2
        bottom = target_size[0] - resized.shape[0] - top
        left = (target_size[1] - resized.shape[1]) // 2
        right = target_size[1] - resized.shape[1] - left

        padded = cv2.copyMakeBorder(
            resized,
            top, bottom, left, right,
            borderType=cv2.BORDER_CONSTANT,
            value=0  # 검정색
        )

        # 저장 (PNG로 통일)
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        output_png_path = os.path.join(output_path, f"{base_filename}.png")
        cv2.imwrite(output_png_path, padded)
        logger.info(f"Processed and saved: {output_png_path}")

    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}")

def preprocess_folder(input_dir, output_dir, target_size=(1024, 1024)):
    ensure_dir(output_dir)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            input_path = os.path.join(input_dir, filename)
            preprocess_image(input_path, output_dir, target_size)

if __name__ == "__main__":
    preprocess_folder('./input_images', './processed_images')