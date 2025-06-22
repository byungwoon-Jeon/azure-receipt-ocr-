import threading
from utils.download_image import download_image_from_url
from utils.preprocess_image import preprocess_image_for_ocr
from utils.crop_with_yolo import crop_receipt_with_yolo
from utils.call_azure_ocr import call_azure_receipt_model
from utils.postprocess_azure_json import postprocess_azure_json

def wrapper_process(input_dict: dict):
    links = input_dict.get("links", [])
    download_dir = input_dict["download_dir"]
    pre_dir = input_dict["preprocessed_dir"]
    crop_dir = input_dict["cropped_dir"]
    ocr_dir = input_dict["ocr_result_dir"]
    post_dir = input_dict["postprocess_dir"]
    endpoint = input_dict["endpoint"]
    key = input_dict["key"]

    def process_single_link(link):
        print(f"[START] Processing {link}")
        # 1. 다운로드
        res1 = download_image_from_url(link, download_dir)
        if not res1["success"]:
            print(f"[ERROR] Download failed: {res1['error']}")
            return
        image_path = res1["saved_path"]

        # 2. 전처리
        res2 = preprocess_image_for_ocr(image_path, pre_dir)
        if not res2["success"]:
            print(f"[ERROR] Preprocess failed: {res2['error']}")
            return
        pre_path = res2["saved_path"]

        # 3. 크롭
        crop_results = crop_receipt_with_yolo(pre_path, crop_dir)
        if not crop_results["success"]:
            print(f"[ERROR] Cropping failed: {crop_results['error']}")
            return

        # 4. OCR + 후처리 (여러 개 크롭된 경우 각각 처리)
        for cropped_path in crop_results["saved_paths"]:
            ocr_result = call_azure_receipt_model(
                cropped_path, ocr_dir, endpoint, key
            )
            if not ocr_result["success"]:
                print(f"[ERROR] OCR failed: {ocr_result['error']}")
                continue

            post_result = postprocess_azure_json(
                ocr_result["saved_path"], post_dir
            )
            if not post_result["success"]:
                print(f"[ERROR] Postprocess failed: {post_result['error']}")
            else:
                print(f"[SUCCESS] Processed {link} → {post_result['saved_path']}")

    # 병렬 처리
    threads = []
    for link in links:
        t = threading.Thread(target=process_single_link, args=(link,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    print("[DONE] All links processed.")
