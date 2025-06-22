import os
import requests
from urllib.parse import urlparse
from datetime import datetime

# ──────────────── 로그 훅 예시 ────────────────
def log_info(msg):
    pass

def log_error(msg):
    pass
# ─────────────────────────────────────────────


def download_file_from_url(url: str, save_dir: str) -> dict:
    """
    단일 URL 파일 다운로드

    Parameters
    ----------
    url : str
        다운로드할 파일의 URL
    save_dir : str
        저장할 디렉터리

    Returns
    -------
    dict
        {
            "success": True/False,
            "saved_path": "저장된_경로" or None,
            "error": None or "에러메시지"
        }
    """
    try:
        os.makedirs(save_dir, exist_ok=True)

        # [HOOK] 저장 폴더 생성/확인
        # log_info(f"[DL] save_dir={save_dir}")

        filename = os.path.basename(urlparse(url).path)
        ext = os.path.splitext(filename)[-1] or ".jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"image_{timestamp}{ext}"
        save_path = os.path.join(save_dir, new_filename)

        # [HOOK] 다운로드 시작
        # log_info(f"[DL] start | url={url} -> {save_path}")

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        # [HOOK] 다운로드 성공
        # log_info(f"[DL] success | saved={save_path}")

        return {"success": True, "saved_path": save_path, "error": None}

    except Exception as e:
        # [HOOK] 다운로드 실패
        # log_error(f"[DL] fail | url={url} | error={e}")
        return {"success": False, "saved_path": None, "error": str(e)}
