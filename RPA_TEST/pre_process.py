import os
import requests
import logging
import traceback
from urllib.parse import urlparse
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger("PRE_PRE_PROCESS")

def validate_file_size(path: str):
    logger.info("[시작] validate_file_size")
    size = os.path.getsize(path)
    if size >= 10 * 1024 * 1024:
        raise ValueError(f"파일 크기가 10MB 이상입니다: {size} bytes")
    logger.info("[종료] validate_file_size")

def download_file_from_url(url: str, save_dir: str, is_file_path: bool = False) -> str:
    """
    지정한 URL로부터 파일을 다운로드하여 save_dir에 저장한 후, 저장된 파일 경로를 반환합니다.

    입력:
    - url (str): 다운로드할 파일 URL. is_file_path가 True이면 이 경로 앞에 기본 서버 주소가 추가됩니다.
    - save_dir (str): 파일을 저장할 디렉토리 경로.
    - is_file_path (bool): URL이 절대 경로가 아닌 서버 파일 경로일 경우 True로 설정합니다.

    출력:
    - str: 다운로드되어 저장된 파일의 경로.
    """
    logger.info("[시작] download_file_from_url")
    try:
        if url.upper().startswith("R"):
            logger.info("R로 시작하는 URL 무시됨")
            return None

        if is_file_path and not url.lower().startswith("http"):
            url = "http://apv.skhynix.com" + url

        if "@" in url:
            url = url.split("@")[0]

        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.basename(urlparse(url).path)
        save_path = os.path.join(save_dir, filename)

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)

        validate_file_size(save_path)  # 10MB 초과 검사
        logger.info("[종료] download_file_from_url")
        return save_path

    except Exception as e:
        logger.error(f"[ERROR] 파일 다운로드 실패: {url} - {e}")
        traceback.print_exc()
        return None

def convert_to_png(input_path: str, save_dir: str) -> str:
    """
    주어진 이미지 파일(input_path)을 PNG 형식으로 변환하여 save_dir 디렉토리에 저장하고, 변환된 PNG 파일 경로를 반환합니다.

    입력:
    - input_path (str): 원본 이미지 파일 경로.
    - save_dir (str): 변환된 PNG 파일을 저장할 디렉토리 경로.

    출력:
    - str: 변환된 PNG 이미지 파일의 경로.
    """
    logger.info("[시작] convert_to_png")
    os.makedirs(save_dir, exist_ok=True)
    filename = os.path.splitext(os.path.basename(input_path))[0] + ".png"
    save_path = os.path.join(save_dir, filename)
    with Image.open(input_path) as img:
        img.convert("RGB").save(save_path, "PNG")
    logger.info("[종료] convert_to_png")
    return save_path

def crop_receipts_with_yolo(
    model: YOLO,
    png_path: str,
    file_type: str,
    base_filename: str,
    original_img: Image.Image,
    fiid: str,
    line_index: int,
    gubun: str,
    receipt_index: int or None,
    common_yn: int,
    cropped_dir: str
) -> list:
    """
    입력 이미지를 대상으로 YOLO 모델을 사용하여 영수증 영역을 검출하고 잘라낸 후, 잘라낸 이미지들의 정보를 리스트로 반환합니다.
    file_type에 따라 처리 방식이 다르며, ATTACH_FILE의 경우 한 이미지당 하나의 영수증만 처리하고, FILE_PATH의 경우 여러 영수증을 처리합니다.

    입력:
    - model (YOLO): YOLO 모델 객체.
    - png_path (str): 처리 대상 이미지 파일 (PNG) 경로.
    - file_type (str): "ATTACH_FILE" 또는 "FILE_PATH" 중 하나로, 첨부 파일인지 경로 파일인지 구분.
    - base_filename (str): 출력 파일 이름의 기본 (확장자 및 인덱스 제외).
    - original_img (PIL.Image.Image): 원본 이미지 객체 (이미 로드된 PIL Image).
    - fiid (str): 영수증이 속한 FIID 식별자.
    - line_index (int): 영수증이 속한 LINE_INDEX 값.
    - gubun (str): 구분 값 (예: "Y" 등).
    - receipt_index (int 또는 None): ATTACH_FILE의 경우 영수증 순번 (일반적으로 1), FILE_PATH의 경우 None (자동 결정됨).
    - common_yn (int): 첨부 파일 여부 플래그 (ATTACH_FILE은 0, FILE_PATH는 1).
    - cropped_dir (str): 잘라낸 이미지 파일을 저장할 디렉토리 경로.

    출력:
    - list: 검출/크롭 결과 딕셔너리들의 리스트. 각 딕셔너리는 성공 시 "file_path" 및 입력 식별자(FIID, LINE_INDEX 등)를 포함하고, 검출 실패나 오류 시 "RESULT_CODE"와 "RESULT_MESSAGE"를 포함합니다.
    """
    logger.info("[시작] crop_receipts_with_yolo")
    results = []
    try:
        yolo_results = model(png_path)
        boxes = yolo_results[0].boxes

        if boxes is None or len(boxes) == 0:
            logger.warning("YOLO 탐지 결과 없음")
            results.append({
                "FIID": fiid, "LINE_INDEX": line_index, "GUBUN": gubun,
                "RECEIPT_INDEX": None, "COMMON_YN": common_yn,
                "RESULT_CODE": "E001",
                "RESULT_MESSAGE": "YOLO 탐지 결과 없음"
            })
            logger.info("[종료] crop_receipts_with_yolo")
            return results

        os.makedirs(cropped_dir, exist_ok=True)

        if file_type == "ATTACH_FILE":
            if len(boxes) > 1:
                logger.warning(f"YOLO 결과 {len(boxes)}개 발견 (ATTACH_FILE는 1개만 가능)")
                results.append({
                    "FIID": fiid, "LINE_INDEX": line_index, "GUBUN": gubun,
                    "RECEIPT_INDEX": None, "COMMON_YN": common_yn,
                    "RESULT_CODE": "E002",
                    "RESULT_MESSAGE": f"YOLO 결과 {len(boxes)}개 발견 (ATTACH_FILE는 1개만 가능)"
                })
                logger.info("[종료] crop_receipts_with_yolo")
                return results

            box_coords = boxes[0].xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, box_coords)
            cropped_img = original_img.crop((x1, y1, x2, y2))
            cropped_path = os.path.join(cropped_dir, f"{base_filename}_receipt.png")
            cropped_img.save(cropped_path)
            validate_file_size(cropped_path)  # 크롭 후 크기 체크

            results.append({
                "FIID": fiid, "LINE_INDEX": line_index, "GUBUN": gubun,
                "RECEIPT_INDEX": receipt_index or 1,
                "COMMON_YN": common_yn,
                "file_path": cropped_path
            })

        elif file_type == "FILE_PATH":
            for idx, box in enumerate(boxes, 1):
                box_coords = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, box_coords)
                cropped_img = original_img.crop((x1, y1, x2, y2))
                cropped_path = os.path.join(cropped_dir, f"{base_filename}_r{idx}.png")
                cropped_img.save(cropped_path)
                validate_file_size(cropped_path)

                results.append({
                    "FIID": fiid, "LINE_INDEX": line_index, "GUBUN": gubun,
                    "RECEIPT_INDEX": idx,
                    "COMMON_YN": common_yn,
                    "file_path": cropped_path
                })

    except Exception as e:
        logger.error(f"[ERROR] YOLO 크롭 오류: {e}")
        traceback.print_exc()
    logger.info("[종료] crop_receipts_with_yolo")
    return results

def run_pre_pre_process(in_params: dict, db_record: dict) -> list:
    """
    주어진 데이터베이스 레코드(db_record)에 대해 전처리 및 YOLO 모델 기반 이미지를 분할(crop)하는 과정을 수행합니다.
    ATTACH_FILE와 FILE_PATH 두 유형에 대해 각각 이미지를 다운로드 및 PNG 변환한 후, YOLO를 통해 영수증 영역을 잘라냅니다.

    입력:
    - in_params (dict): 전처리 및 모델 관련 설정값들이 담긴 딕셔너리 (output_dir, preprocessed_dir, cropped_dir, yolo_model_path 등 필수).
    - db_record (dict): 처리 대상 DB 레코드 (FIID, LINE_INDEX, GUBUN, ATTACH_FILE, FILE_PATH 등의 키를 포함).

    출력:
    - list: YOLO 검출 및 크롭 결과 딕셔너리들의 리스트. 영수증 이미지가 성공적으로 잘려진 경우 각 결과에는 "file_path"와 식별 정보(FIID, LINE_INDEX 등)가 포함되며, 검출 실패 시 "RESULT_CODE"와 "RESULT_MESSAGE"를 포함한 항목이 들어갑니다.
    """
    logger.info("[시작] run_pre_pre_process")
    try:
        download_dir = in_params["download_dir"]
        model_path = in_params["yolo_model_path"]
        model = YOLO(model_path)

        fiid = db_record["FIID"]
        line_index = db_record["LINE_INDEX"]
        gubun = db_record["GUBUN"]

        results = []

        for file_type in ["ATTACH_FILE", "FILE_PATH"]:
            url = db_record.get(file_type)
            if not url:
                continue

            common_yn = 0 if file_type == "ATTACH_FILE" else 1
            receipt_index = 1 if file_type == "ATTACH_FILE" else None

            orig_path = download_file_from_url(url, download_dir, is_file_path=(file_type == "FILE_PATH"))
            if not orig_path:
                logger.info(f"[{file_type}] URL 다운로드 스킵됨")
                continue

            png_path = convert_to_png(orig_path, download_dir)
            with Image.open(png_path) as original_img:
                base_filename = os.path.splitext(os.path.basename(png_path))[0]
                cropped_dir = os.path.join(download_dir, "cropped")
                result = crop_receipts_with_yolo(
                    model=model,
                    png_path=png_path,
                    file_type=file_type,
                    base_filename=base_filename,
                    original_img=original_img,
                    fiid=fiid,
                    line_index=line_index,
                    gubun=gubun,
                    receipt_index=receipt_index,
                    common_yn=common_yn,
                    cropped_dir=cropped_dir
                )
                results.extend(result)

        logger.info("[종료] run_pre_pre_process")
        return results

    except Exception as e:
        logger.error(f"[ERROR] 전처리 실패: {e}")
        traceback.print_exc()
        return []

if __name__ == "__main__":
    from pprint import pprint

    # ✅ in_params 설정
    in_params = {
        "output_dir": "./test_output",           # 다운로드된 원본 저장 경로
        "preprocessed_dir": "./test_preproc",    # PNG 변환 이미지 저장 경로
        "cropped_dir": "./test_cropped",         # YOLO 크롭 이미지 저장 경로
        "yolo_model_path": "./yolo/best.pt"      # YOLO 모델 경로 (.pt 파일)
    }

    # ✅ db_record 입력 샘플 (ATTACH_FILE만 있는 경우)
    db_record = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "GUBUN": "Y",
        "ATTACH_FILE": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Brandon_Sanderson_signing.jpg/640px-Brandon_Sanderson_signing.jpg",  # 테스트용 이미지
        "FILE_PATH": None
    }

    print("🚀 run_pre_pre_process() 테스트 시작")
    result = run_pre_pre_process(in_params, db_record)

    print("\n📄 결과 리스트:")
    pprint(result)

    # 결과 이미지 경로 확인
    print("\n🖼 크롭된 이미지 파일들:")
    for r in result:
        if "file_path" in r:
            print("✔", r["file_path"])
        else:
            print("❌ 오류:", r)
