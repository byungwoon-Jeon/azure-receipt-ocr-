from pathlib import Path
from utils.preprocess_image import preprocess_image_for_ocr
from utils.crop_with_yolo import crop_receipt_with_yolo
from utils.call_azure_ocr import call_azure_receipt_model
from utils.postprocess_azure_json import postprocess_azure_json
from util import idp_utils   # 회사 다운로드·로깅 모듈

def process_receipt_pipeline(input_dict: dict):
    """
    links                : 이미지 URL 리스트
    download_dir/…       : 단계별 저장 폴더
    endpoint / key       : Azure OCR 인증 정보
    """
    links          = input_dict["links"]
    download_dir   = Path(input_dict["download_dir"])
    pre_dir        = Path(input_dict["preprocessed_dir"])
    crop_dir       = Path(input_dict["cropped_dir"])
    ocr_dir        = Path(input_dict["ocr_result_dir"])
    post_dir       = Path(input_dict["postprocess_dir"])
    endpoint       = input_dict["endpoint"]
    key            = input_dict["key"]

    # 폴더 미리 생성
    for d in (download_dir, pre_dir, crop_dir, ocr_dir, post_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1️⃣ ── 다운로드(멀티쓰레드) ──────────────────────────
    dl_params = []
    for url in links:
        save_path = download_dir / url.split("/")[-1]
        dl_params.append({"downloadurl": url,
                          "savepath": str(save_path)})
    download_results = run_in_multi_thread(
        idp_utils.download_file_url, dl_params, max_threads=5)

    # 2️⃣ ── 나머지 단계는 링크별 순차 처리 (실패·성공 로그 포함) ───
    for idx, dl_res in enumerate(download_results):
        if isinstance(dl_res, Exception) or not dl_res:
            logger.error(f"[DL-FAIL] idx={idx}  url={links[idx]}")
            continue
        img_path = dl_res                      # 회사 함수는 'save_file_path' str 반환

        # 전처리
        pre_res = preprocess_image_for_ocr(img_path, str(pre_dir))
        if not pre_res["success"]:
            logger.error(f"[PP-FAIL] {pre_res['error']}  ({img_path})")
            continue
        pre_path = pre_res["saved_path"]

        # 크롭
        crop_res = crop_receipt_with_yolo(pre_path, str(crop_dir))
        if not crop_res["success"]:
            logger.error(f"[CROP-FAIL] {crop_res['error']} ({pre_path})")
            continue

        # 각 크롭 → OCR → 후처리
        for cp in crop_res["saved_paths"]:
            ocr_res = call_azure_receipt_model(cp, str(ocr_dir),
                                               endpoint, key)
            if not ocr_res["success"]:
                logger.error(f"[OCR-FAIL] {ocr_res['error']} ({cp})")
                continue

            post_res = postprocess_azure_json(ocr_res["saved_path"],
                                              str(post_dir))
            if post_res["success"]:
                logger.info(f"[OK] {links[idx]} → {post_res['saved_path']}")
            else:
                logger.error(f"[POST-FAIL] {post_res['error']} ({cp})")