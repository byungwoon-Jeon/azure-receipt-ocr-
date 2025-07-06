from PIL import Image
import os
import logging
import traceback
from ultralytics import YOLO

def run_yolo_crop(in_params: dict, input_record: dict) -> list or dict:
    """
    YOLO로 영수증 감지 및 크롭 수행
    Args:
        in_params (dict): {
            "cropped_dir": 크롭 이미지 저장 디렉토리,
            "yolo_model_path": YOLO 모델 경로
        }
        input_record (dict): {
            "FIID", "LINE_INDEX", "RECEIPT_INDEX", "COMMON_YN", "file_type", "file_path"
        }

    Returns:
        list of dict (성공 시) or dict (에러 코드 포함)
    """
    logger = logging.getLogger("YOLO_CROP")
    logger.setLevel(logging.DEBUG)

    try:
        assert "cropped_dir" in in_params, "'cropped_dir' 키가 없습니다."
        assert "yolo_model_path" in in_params, "'yolo_model_path' 키가 없습니다."

        cropped_dir = in_params["cropped_dir"]
        model_path = in_params["yolo_model_path"]
        os.makedirs(cropped_dir, exist_ok=True)

        # YOLO 모델 로딩 (최초 1회만 권장 – 외부에서 캐싱해도 좋음)
        model = YOLO(model_path)

        # 입력 데이터 추출
        file_path = input_record["file_path"]
        file_type = input_record["file_type"]
        fiid = input_record["FIID"]
        line_index = input_record["LINE_INDEX"]
        common_yn = input_record["COMMON_YN"]

        # YOLO 객체 탐지
        results = model(file_path)
        boxes = results[0].boxes

        if boxes is None or len(boxes) == 0:
            return {
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "RECEIPT_INDEX": None,
                "COMMON_YN": common_yn,
                "RESULT_CODE": "E001",
                "RESULT_MESSAGE": "YOLO 탐지 결과 없음"
            }

        # 이미지 로드 및 크롭 준비
        original_img = Image.open(file_path)
        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        if file_type == "ATTACH_FILE":
            # 라인아이템: 반드시 박스 1개만 존재해야 함
            if len(boxes) > 1:
                return {
                    "FIID": fiid,
                    "LINE_INDEX": line_index,
                    "RECEIPT_INDEX": None,
                    "COMMON_YN": common_yn,
                    "RESULT_CODE": "E002",
                    "RESULT_MESSAGE": f"YOLO 결과 {len(boxes)}개 (ATTACH_FILE는 1개만 가능)"
                }

            box = boxes[0].xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, box)
            cropped_img = original_img.crop((x1, y1, x2, y2))

            cropped_path = os.path.join(cropped_dir, f"{base_filename}.png")
            cropped_img.save(cropped_path)

            return [{
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "RECEIPT_INDEX": input_record.get("RECEIPT_INDEX", 1),
                "COMMON_YN": common_yn,
                "file_path": cropped_path
            }]

        elif file_type == "FILE_PATH":
            # 공통아이템: 박스 개수만큼 크롭
            result_list = []
            for idx, box in enumerate(boxes):
                coords = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, coords)
                cropped_img = original_img.crop((x1, y1, x2, y2))

                cropped_path = os.path.join(cropped_dir, f"{base_filename}_{idx + 1}.png")
                cropped_img.save(cropped_path)

                result_list.append({
                    "FIID": fiid,
                    "LINE_INDEX": line_index,
                    "RECEIPT_INDEX": idx + 1,
                    "COMMON_YN": common_yn,
                    "file_path": cropped_path
                })

            return result_list

        else:
            return {
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "RECEIPT_INDEX": None,
                "COMMON_YN": common_yn,
                "RESULT_CODE": "E003",
                "RESULT_MESSAGE": f"file_type 값 이상: {file_type}"
            }

    except Exception as e:
        logger.error(f"YOLO 크롭 실패: {traceback.format_exc()}")
        return {
            "FIID": input_record.get("FIID"),
            "LINE_INDEX": input_record.get("LINE_INDEX"),
            "RECEIPT_INDEX": None,
            "COMMON_YN": input_record.get("COMMON_YN"),
            "RESULT_CODE": "E999",
            "RESULT_MESSAGE": f"예외 발생: {e}"
        }

if __name__ == "__main__":
    from pprint import pprint

    # 테스트용 YOLO 모델 경로와 디렉토리
    in_params = {
        "cropped_dir": "C:/Users/quddn/Downloads/test/cropped",  # YOLO 크롭 결과 저장 위치
        "yolo_model_path": "C:/Users/quddn/Downloads/test/best.pt"  # YOLO 모델 경로
    }

    # 테스트용 라인아이템 PNG
    input_record_line = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "RECEIPT_INDEX": None,  # ← ATTACH_FILE은 조건에 따라 1 or None
        "COMMON_YN": 0,
        "file_type": "ATTACH_FILE",
        "file_path": "C:/Users/quddn/Downloads/test/preprocessed/라인아이템.png"
    }

    # 테스트용 공통아이템 PNG
    input_record_common = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "RECEIPT_INDEX": None,
        "COMMON_YN": 1,
        "file_type": "FILE_PATH",
        "file_path": "C:/Users/quddn/Downloads/test/preprocessed/공통아이템.png"
    }

    print("🧪 라인아이템 테스트 중...")
    result_line = run_yolo_crop(in_params, input_record_line)
    pprint(result_line)

    print("\n🧪 공통아이템 테스트 중...")
    result_common = run_yolo_crop(in_params, input_record_common)
    pprint(result_common)