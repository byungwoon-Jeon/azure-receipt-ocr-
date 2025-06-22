import os
import requests
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

def _download_single_file(url: str, save_dir: str) -> tuple:
    """
    내부용: 단일 파일 다운로드 함수
    return: (success(bool), saved_path(str), error(str or None), url)
    """

    try:
        os.makedirs(save_dir, exist_ok=True)

        # [HOOK] 폴더 생성 시 로깅 가능
        # ex) logging.info(f"저장 폴더 생성: {save_dir}")

        filename = os.path.basename(urlparse(url).path)
        ext = os.path.splitext(filename)[-1] or ".jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"image_{timestamp}{ext}"
        save_path = os.path.join(save_dir, new_filename)

        # [HOOK] 다운로드 시작 로그
        # ex) logging.info(f"다운로드 시작 | URL: {url} → {save_path}")

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)

        # [HOOK] 다운로드 성공 로그
        # ex) logging.info(f"다운로드 성공 | 저장 경로: {save_path}")

        return True, save_path, None, url

    except Exception as e:
        # [HOOK] 다운로드 실패 로그
        # ex) logging.error(f"다운로드 실패 | URL: {url} | 에러: {e}")
        return False, None, str(e), url


def download_from_links(input_dict: dict) -> str:
    """
    📦 다운로드 유틸 함수 (단일/다중 자동 분기)
    """
    save_dir = input_dict.get("save_dir")
    urls = input_dict.get("urls")

    # [HOOK] 입력값 확인 로그
    # ex) logging.info(f"입력값 확인 | save_dir={save_dir} | urls={urls}")

    if not save_dir or not urls:
        return "success=false; saved_path=; error=입력값에 'save_dir' 또는 'urls'가 없습니다"

    if isinstance(urls, str):
        urls = [urls]

    if len(urls) == 1:
        # [HOOK] 단일 파일 다운로드 시작 로그
        # ex) logging.info("단일 다운로드 처리 시작")

        success, saved_path, error, _ = _download_single_file(urls[0], save_dir)

        # [HOOK] 단일 다운로드 결과 로그
        # ex) logging.info(f"결과 | success={success}, saved_path={saved_path}, error={error}")

        return f"success={str(success).lower()}; saved_path={saved_path or ''}; error={error or ''}"

    else:
        # [HOOK] 멀티 다운로드 시작 로그
        # ex) logging.info(f"다중 다운로드 시작 | 링크 수: {len(urls)}")

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_download_single_file, url, save_dir) for url in urls]
            for future in futures:
                results.append(future.result())

        success_count = sum(1 for r in results if r[0])
        saved_paths = [r[1] for r in results if r[0]]
        failed_urls = [r[3] for r in results if not r[0]]

        # [HOOK] 멀티 다운로드 결과 요약 로그
        # ex) logging.info(f"다중 다운로드 완료 | 성공: {success_count}, 실패: {len(failed_urls)}")

        return (
            f"success={success_count}/{len(urls)}; "
            f"saved_paths={saved_paths}; "
            f"failed_urls={failed_urls}"
        )
