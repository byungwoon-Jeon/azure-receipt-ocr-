import os
import requests
import logging
import traceback
from urllib.parse import urlparse
from PIL import Image

def download_file_from_url(url: str, save_dir: str, is_file_path=False) -> str:
    """
    주어진 URL에서 파일을 다운로드하여 지정된 디렉토리에 저장
    FILE_PATH인 경우 기본 도메인(http://apv.skhynix.com) 붙여줌

    Args:
        url (str): 다운로드할 파일 URL
        save_dir (str): 저장 디렉토리 경로
        is_file_path (bool): FILE_PATH 여부 (True이면 도메인 보정)

    Returns:
        str: 저장된 파일 경로
    """
    if is_file_path and not url.startswith("http"):
        url = "http://apv.skhynix.com" + url

    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    save_path = os.path.join(save_dir, filename)

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    with open(save_path, "wb") as f:
        f.write(response.content)

    return save_path


def convert_to_png(input_path: str, save_dir: str, logger=None) -> str:
    """
    이미지 파일을 PNG로 변환 후 저장

    Args:
        input_path (str): 원본 이미지 경로
        save_dir (str): 저장할 디렉토리 경로
        logger: 로깅 객체 (선택)

    Returns:
        str: 저장된 PNG 경로
    """
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

    Args:
        in_params (dict): {
            "db_data": dict,  # DB 레코드 1건
            "output_dir": str,  # 원본 이미지 저장 경로
            "preprocessed_dir": str,  # PNG 이미지 저장 경로
            "python_log_file_path": str (optional)  # 로그 파일 경로
        }

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

        # 입력값 검증
        assert "db_data" in in_params, "[ERROR] 'db_data' 키가 없습니다."
        assert "output_dir" in in_params, "[ERROR] 'output_dir' 키가 없습니다."
        assert "preprocessed_dir" in in_params, "[ERROR] 'preprocessed_dir' 키가 없습니다."

        db_data = in_params["db_data"]
        output_dir = in_params["output_dir"]
        preprocessed_dir = in_params["preprocessed_dir"]

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(preprocessed_dir, exist_ok=True)

        results = []

        fiid = db_data.get("FIID")
        line_index = db_data.get("SEQ")
        has_common_item = bool(db_data.get("FILE_PATH"))

        for file_type in ["ATTACH_FILE", "FILE_PATH"]:
            url = db_data.get(file_type)
            if url:
                try:
                    is_file_path = file_type == "FILE_PATH"
                    original_path = download_file_from_url(url, output_dir, is_file_path)
                    logger.info(f"[{file_type}] 다운로드 성공: {original_path}")

                    png_path = convert_to_png(original_path, preprocessed_dir, logger)

                    # RECEIPT_INDEX, COMMON_YN 설정
                    if file_type == "ATTACH_FILE":
                        receipt_index = 1 if has_common_item else None
                        common_yn = 0
                    else:  # FILE_PATH
                        receipt_index = None
                        common_yn = 1

                    results.append({
                        "FIID": fiid,
                        "LINE_INDEX": line_index,
                        "RECEIPT_INDEX": receipt_index,
                        "COMMON_YN": common_yn,
                        "file_type": file_type,
                        "file_path": png_path
                    })

                except Exception as e:
                    logger.error(f"[{file_type}] 처리 실패: {url} → {e}")
            else:
                logger.info(f"[{file_type}] URL 없음 → 스킵")

        if not results:
            raise ValueError("[ERROR] ATTACH_FILE, FILE_PATH 모두 없음 → 처리 불가")

        return results

    except Exception as e:
        logger.error(f"[FATAL] 전처리 실패: {traceback.format_exc()}")
        return []

if __name__ == "__main__":
    in_params = {
        "db_data": {
            "FIID": "TEST001",
            "SEQ": 1,
            "ATTACH_FILE": "https://example.com/test.jpg",
            "FILE_PATH": "/GWStorage/e-sign/sample.jpg",  # ← 자동 도메인 추가됨
            "COMMON_YN": 1
        },
        "output_dir": "./output",  # 원본 저장 위치
        "preprocessed_dir": "./preprocessed",  # PNG 저장 위치
        "python_log_file_path": "./preprocess_log.txt"
    }

    result = run_pre_process(in_params)
    print("📄 다운로드 및 전처리 결과:")
    for r in result:
        print(r)
