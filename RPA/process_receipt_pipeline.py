import threading
from util import idp_utils  # run_in_multi_thread, wrapped_func 포함
from utils.download_image import download_image_from_url
from utils.preprocess_image import preprocess_image_for_ocr
from utils.crop_with_yolo import crop_receipt_with_yolo
from utils.call_azure_ocr import call_azure_receipt_model
from utils.postprocess_azure_json import postprocess_azure_json

logger = idp_utils.setup_logger("wrapper_process")

def process_single_receipt(in_params: dict):
    link = in_params["link"]
    download_dir = in_params["download_dir"]
    pre_dir = in_params["preprocessed_dir"]
    crop_dir = in_params["cropped_dir"]
    ocr_dir = in_params["ocr_result_dir"]
    post_dir = in_params["postprocess_dir"]
    endpoint = in_params["endpoint"]
    key = in_params["key"]

    logger.debug(f"[START] Processing {link}")

    # 1. 다운로드
    download_params = {"downloadurl": link, "savepath": f"{download_dir}/{idp_utils.get_filename_from_url(link)}"}
    try:
        image_path = idp_utils.download_file_url(download_params)
    except Exception as e:
        logger.error(f"[ERROR] Download failed for {link}: {e}")
        return

    # 2. 전처리
    res2 = preprocess_image_for_ocr(image_path, pre_dir)
    if not res2["success"]:
        logger.error(f"[ERROR] Preprocess failed for {link}: {res2['error']}")
        return
    pre_path = res2["saved_path"]

    # 3. 크롭
    crop_results = crop_receipt_with_yolo(pre_path, crop_dir)
    if not crop_results["success"]:
        logger.error(f"[ERROR] Cropping failed for {link}: {crop_results['error']}")
        return

    # 4. OCR + 후처리 (여러 개 크롭된 경우 각각 처리)
    for cropped_path in crop_results["saved_paths"]:
        ocr_result = call_azure_receipt_model(cropped_path, ocr_dir, endpoint, key)
        if not ocr_result["success"]:
            logger.error(f"[ERROR] OCR failed for {cropped_path}: {ocr_result['error']}")
            continue

        post_result = postprocess_azure_json(ocr_result["saved_path"], post_dir)
        if not post_result["success"]:
            logger.error(f"[ERROR] Postprocess failed for {cropped_path}: {post_result['error']}")
        else:
            logger.info(f"[SUCCESS] Processed {link} → {post_result['saved_path']}")


def wrapper_process(input_dict: dict):
    links = input_dict.get("links", [])
    common_params = {
        "download_dir": input_dict["download_dir"],
        "preprocessed_dir": input_dict["preprocessed_dir"],
        "cropped_dir": input_dict["cropped_dir"],
        "ocr_result_dir": input_dict["ocr_result_dir"],
        "postprocess_dir": input_dict["postprocess_dir"],
        "endpoint": input_dict["endpoint"],
        "key": input_dict["key"],
    }

    param_list = []
    for link in links:
        single = {"link": link}
        single.update(common_params)
        param_list.append(single)

    logger.info(f"[START] 총 {len(param_list)}개 작업 병렬 실행 시작")
    idp_utils.run_in_multi_thread(process_single_receipt, param_list)
    logger.info("[DONE] 모든 작업 완료")