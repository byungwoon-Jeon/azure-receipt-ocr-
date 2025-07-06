import os
import requests
import logging
import traceback
from urllib.parse import urlparse
from PIL import Image

def download_file_from_url(url: str, save_dir: str) -> str:
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    save_path = os.path.join(save_dir, filename)

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    with open(save_path, "wb") as f:
        f.write(response.content)

    return save_path

def convert_to_png(input_path: str, save_dir: str, logger=None) -> str:
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.splitext(os.path.basename(input_path))[0]
    save_path = os.path.join(save_dir, f"{filename}.png")

    with Image.open(input_path) as img:
        img.convert("RGB").save(save_path, "PNG")

    if logger:
        logger.info(f"PNG 변환 완료: {save_path}")

    return save_path

def run_pre_process(in_params: dict) -> list:
    """
    전처리 단계: 이미지 다운로드 → PNG 변환 → 결과 dict 리스트 반환

    Returns:
        list of dict: [
            {
                "FIID": str,
                "LINE_INDEX": int,
                "RECEIPT_INDEX": int or None,
                "COMMON_YN": int,
                "file_type": str,
                "file_path": str
            }, ...
        ]
    """
    logger = logging.getLogger("PRE_PROCESS")
    logger.setLevel(logging.DEBUG)

    try:
        log_path = in_params.get("python_log_file_path")
        if log_path:
            handler = logging.FileHandler(log_path)
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            if not logger.handlers:
                logger.addHandler(handler)

        assert "db_data" in in_params, "'db_data' 키가 없습니다."
        assert "output_dir" in in_params, "'output_dir' 키가 없습니다."
        assert "preprocessed_dir" in in_params, "'preprocessed_dir' 키가 없습니다."

        db_data = in_params["db_data"]
        output_dir = in_params["output_dir"]
        preprocessed_dir = in_params["preprocessed_dir"]

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(preprocessed_dir, exist_ok=True)

        results = []

        fiid = db_data["FIID"]
        line_index = db_data["SEQ"]
        common_yn = db_data["COMMON_YN"]
        has_common_item = bool(db_data.get("FILE_PATH"))

        for file_type, key in [("ATTACH_FILE", "ATTACH_FILE"), ("FILE_PATH", "FILE_PATH")]:
            url = db_data.get(key)
            if url:
                try:
                    original_path = download_file_from_url(url, output_dir)
                    logger.info(f"[{file_type}] 다운로드 성공: {original_path}")

                    png_path = convert_to_png(original_path, preprocessed_dir, logger)

                    if file_type == "ATTACH_FILE":
                        receipt_index = 1 if has_common_item else None
                    else:  # FILE_PATH
                        receipt_index = None  # YOLO 이후 결정

                    results.append({
                        "FIID": fiid,
                        "LINE_INDEX": line_index,
                        "RECEIPT_INDEX": receipt_index,
                        "COMMON_YN": common_yn if file_type == "ATTACH_FILE" else 1,
                        "file_type": file_type,
                        "file_path": png_path
                    })

                except Exception as e:
                    logger.error(f"[{file_type}] 처리 실패: {url} → {e}")
            else:
                logger.info(f"[{file_type}] URL 없음 → 스킵")

        if not results:
            raise ValueError("ATTACH_FILE, FILE_PATH 모두 없음 → 처리 불가")

        return results

    except Exception as e:
        logger.error(f"전처리 실패: {traceback.format_exc()}")
        return []


in_params = {
    "db_data": {
        "FIID": "TEST001",
        "SEQ": 1,
        "ATTACH_FILE": "C:/Users/quddn/Downloads/test/라인아이템.jpg",
        "FILE_PATH": "C:/Users/quddn/Downloads/test/공통영수증.jpg",
        "COMMON_YN": 1  # 공통아이템 (FILE_PATH 기준으로 후처리할 예정)
    },
    "output_dir": "C:/Users/quddn/Downloads/test",
    "python_log_file_path": "C:/Users/quddn/Downloads/test/python_log_test.txt"
}

if __name__ == "__main__":
    result = run_pre_process(in_params)
    print("다운로드된 파일들:", result)