import os
import requests
import logging
from datetime import datetime
from urllib.parse import urlparse

# ────────────────────────────────
#  로깅 설정
# ────────────────────────────────
logging.basicConfig(
    filename="download.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def download_file_from_url(input_dict: dict) -> str:
    """
    이미지 URL로부터 파일 다운로드 후 저장
    RPA 호환: key=value 형식의 문자열로 결과 반환

    Parameters
    ----------
    input_dict : dict
        {
            "url": "https://example.com/image.jpg",
            "save_dir": "input/"
        }

    Returns
    -------
    str
        "success=true; saved_path=input/파일명.png; error="
        또는
        "success=false; saved_path=; error=에러메시지"
    """
    try:
        url = input_dict.get("url")
        save_dir = input_dict.get("save_dir")

        if not url or not save_dir:
            raise ValueError("input_dict에는 'url'과 'save_dir' 키가 모두 있어야 합니다.")

        os.makedirs(save_dir, exist_ok=True)

        original_name = os.path.basename(urlparse(url).path)
        ext = os.path.splitext(original_name)[-1] or ".jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_{timestamp}{ext}"
        save_path = os.path.join(save_dir, filename)

        logging.info(f"START download | url={url} | save_dir={save_dir} | filename={filename}")

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        logging.info(f"DONE  download | saved_path={save_path}")
        return f"success=true; saved_path={save_path}; error="

    except Exception as e:
        logging.error(f"FAIL download | url={input_dict.get('url')} | error={e}")
        return f"success=false; saved_path=; error={str(e)}"