import os
import cv2
from utils import setup_logger, ensure_dir, is_image_file

# 로거 설정
logger = setup_logger('preprocessing')

# 단일 이미지 처리
def preprocess_image(input_path, output_dir, target_size=(1024, 1024)):
    """
    단일 이미지 파일을 전처리하여 저장
    (그레이 스케일 + 리사이즈 + 패딩)

    Args:
        input_path (str): 원본 이미지 경로
        output_dir (str): 저장할 폴더 경로
        target_size (tuple): 최종 이미지 크기 (기본 : 1024, 1024)
    """
    try:
        img = cv2.imread(input_path)
        if img is None:
            logger.warning(f"[경고] 이미지를 읽을 수 없습니다: {input_path}")
            return
        
        # 그레이 스케일
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 비율 유지 리사이즈
        h, w = gray.shape
        scale = min(target_size[0] / h, target_size[1] / w)
        resized = cv2.resize(gray, (int(w * scale), int(h * scale)))
        
        # 패딩
        top = (target_size[0] - resized.shape[0]) // 2
        bottom = target_size[0] - resized.shape[0] - top
        left = (target_size[1] - resized.shape[1]) // 2
        right = target_size[1] - resized.shape[1] - left
        
        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right,
            borderType=cv2.BORDER_CONSTANT, value=0
        )
        
        # 저장
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base_filename}.png")
        
        success = cv2.imwrite(output_path, padded)
        if success:
            logger.info(f"[완료] 전처리 및 저장 완료: {output_path}")    
        else:
            logger.error(f"[에러] 이미지 저장 실패: {output_path}")
        
    except Exception as e:
        logger.error(f"[에러] {input_path} 처리 중 예외 발생: {e}")
        
    
    # 폴더 단위 전처리
def preprocess_folder(input_dir, output_dir, target_size=(1024, 1024)):
    """
    폴더 내 모든 이미지 파일을 전처리 합니다.

    Args:
        input_dir (str): 원본 이미지 폴더
        output_dir (str): 전처리된 이미지 저장 폴더
        target_size (tuple): 전처리 이미지 크기(기본값 : 1024, 1024)
    """
    try:
        ensure_dir(output_dir, logger)
        
        files = os.listdir(input_dir)
        for filename in files:
            if is_image_file(filename):
                input_path = os.path.join(input_dir, filename)
                preprocess_image(input_path, output_dir, target_size)
        
        logger.info(f"[완료] 전체 폴더 전처리 완료: {input_dir} -> {output_dir}")
    
    except Exception as e:
        logger.exception(f"[예외] 폴더 전처리 중 오류 발생: {e}")
            
# 메인 진입점
if __name__ == "__main__":
    preprocess_folder('./input_images', './processed_images')