import os
from ultralytics import YOLO
from PIL import Image
from datetime import datetime

# ──────────────── 로그 훅 예시 ────────────────
def log_info(msg):
    pass

def log_error(msg):
    pass
# ─────────────────────────────────────────────


def crop_with_yolo(image_path: str, output_dir: str) -> dict:
    """
    YOLOv8 기반 객체 감지 후 크롭 저장

    Parameters
    ----------
    image_path : str
        전처리된 이미지 경로
    output_dir : str
        크롭된 이미지 저장 디렉터리

    Returns
    -------
    dict
        {
            "success": True/False,
            "saved_paths": [...],
            "error": None or "에러 메시지"
        }
    """
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 모델 로드
        model = YOLO("best.pt")

        # 감지 수행
        results = model(image_path)
        boxes = results[0].boxes

        if boxes is None or len(boxes) == 0:
            return {"success": False, "saved_paths": [], "error": "디텍션 결과 없음"}

        saved_paths = []
        image = Image.open(image_path)
        base_name = os.path.splitext(os.path.basename(image_path))[0]

        for idx, box in enumerate(boxes):
            coords = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, coords)
            cropped = image.crop((x1, y1, x2, y2))

            filename = f"{base_name}_crop{idx+1}.png"
            save_path = os.path.join(output_dir, filename)

            cropped.save(save_path)
            saved_paths.append(save_path)

        return {"success": True, "saved_paths": saved_paths, "error": None}

    except Exception as e:
        return {"success": False, "saved_paths": [], "error": str(e)}