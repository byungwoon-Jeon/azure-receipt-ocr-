import os
import cv2
from datetime import datetime

def preprocess_for_azure(input_dict: dict) -> str:
    # ────── [HOOK] 입력값 확인 로깅 위치 ──────
    # ex) log_info(f"[전처리] input_dict: {input_dict}")

    try:
        image_path = input_dict.get("image_path")
        output_dir = input_dict.get("output_dir")

        if not image_path or not output_dir:
            raise ValueError("input_dict에는 'image_path'와 'output_dir' 키가 필요합니다.")

        os.makedirs(output_dir, exist_ok=True)

        # 이미지 로드
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"이미지를 불러올 수 없습니다: {image_path}")

        h, w = img.shape[:2]
        long_side = max(h, w)

        # ────── [HOOK] 원본 이미지 크기 기록 ──────
        # ex) log_info(f"[전처리] 원본 이미지 크기: {w}x{h}")

        # 리사이즈 조건 설정
        target_min = 600
        target_max = 3000

        # 리사이즈 비율 계산
        if long_side < target_min:
            scale = target_min / long_side
        elif long_side > target_max:
            scale = target_max / long_side
        else:
            scale = 1.0

        # 비율 유지 리사이즈
        if scale != 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # ────── [HOOK] 리사이즈 처리 로그 ──────
            # ex) log_info(f"[전처리] 리사이즈 적용: {w}x{h} → {new_w}x{new_h}")

        # 파일명 구성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_{timestamp}.png"
        save_path = os.path.join(output_dir, filename)

        # PNG 저장 (압축률 9: 최대 압축)
        success = cv2.imwrite(save_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        if not success:
            raise IOError("이미지 저장 실패")

        # ────── [HOOK] 저장 완료 로그 ──────
        # ex) log_info(f"[전처리] 저장 완료: {save_path}")

        return f"success=true; saved_path={save_path}; error="

    except Exception as e:
        # ────── [HOOK] 예외 로그 ──────
        # ex) log_error(f"[전처리] 오류 발생: {e}")
        return f"success=false; saved_path=; error={str(e)}"
