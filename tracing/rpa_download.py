import os
import requests
from urllib.parse import urlparse
from datetime import datetime

def download_file_from_url(input_dict):
    """
    RPA에서 호출할 파일 다운로드 함수

    Parameters
    ----------
    input_dict : dict
        {
            "url": "https://example.com/image.jpg",
            "save_dir": "input/"
        }

    Returns
    -------
    dict
        {
            "success": True,
            "saved_path": "input/image_20250617_134501.jpg",
            "error": None
        }
    """
    try:
        url = input_dict.get("url")
        save_dir = input_dict.get("save_dir")

        if not url or not save_dir:
            raise ValueError("입력값에 'url'과 'save_dir' 키가 모두 있어야 합니다.")

        # 디렉토리 생성
        os.makedirs(save_dir, exist_ok=True)

        # 원래 파일 이름 추출 (없으면 날짜 기반 이름)
        original_filename = os.path.basename(urlparse(url).path)
        ext = os.path.splitext(original_filename)[-1] or ".jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_{timestamp}{ext}"
        save_path = os.path.join(save_dir, filename)

        # 다운로드
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 오류 응답 예외 발생

        with open(save_path, "wb") as f:
            f.write(response.content)

        return {
            "success": True,
            "saved_path": save_path,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "saved_path": None,
            "error": str(e)
        }