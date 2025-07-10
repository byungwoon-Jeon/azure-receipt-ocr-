# 📂 wrapper.py
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine
from db_master import query_data_by_date, insert_postprocessed_result
from pre_process import run_pre_process
from YOLO_crop import run_yolo_crop
from doc_process import run_azure_ocr
from post_process import post_process_and_save
from utils.logger_utils import setup_module_logger

def process_single_record(record: dict, in_params: dict):
    logger = setup_module_logger("WRAPPER", in_params["log_dir"], in_params["log_level"])
    try:
        preprocessed = run_pre_process({
            **in_params,
            "db_data": record
        })

        for image_info in preprocessed:
            cropped_list = run_yolo_crop(in_params, image_info)

            for cropped in cropped_list:
                if "RESULT_CODE" in cropped:
                    logger.warning(f"[SKIP] YOLO 오류: {cropped}")
                    continue

                ocr_result = run_azure_ocr(in_params, cropped)
                if ocr_result.get("RESULT_CODE") == "AZURE_ERR":
                    continue

                fiid = cropped["FIID"]
                line_index = cropped["LINE_INDEX"]
                receipt_index = cropped["RECEIPT_INDEX"]
                json_path = os.path.join(
                    in_params["ocr_json_dir"], f"{os.path.splitext(os.path.basename(cropped['file_path']))[0]}.ocr.json"
                )

                post_json = post_process_and_save({
                    **in_params,
                    "postprocess_output_dir": in_params["post_json_dir"]
                }, {
                    **cropped,
                    "json_path": json_path,
                    "ATTACH_FILE": record.get("ATTACH_FILE")
                })

                insert_postprocessed_result(post_json, in_params)

    except Exception as e:
        logger.error(f"[FATAL] 단일 레코드 처리 실패: {record}\n{e}")

def run_wrapper(in_params: dict):
    logger = setup_module_logger("WRAPPER", in_params["log_dir"], in_params["log_level"])

    data_records = query_data_by_date(in_params)
    if not data_records:
        logger.info("📭 처리할 데이터가 없습니다.")
        return

    logger.info(f"총 {len(data_records)}건 처리 시작")
    max_workers = in_params.get("max_workers", 4)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single_record, rec, in_params) for rec in data_records]
        for future in as_completed(futures):
            future.result()

    logger.info("✅ 전체 파이프라인 완료")

if __name__ == "__main__":
    # ✅ SAP HANA용 엔진 구성
    hana_user = "hyrwsgamsa_if"
    hana_pass = "hyrwsgamsaif123!"
    hana_host = "10.158.101.125"
    hana_port = "30047"

    hana_conn_str = f"hdbcli://{hana_user}:{hana_pass}@{hana_host}:{hana_port}"
    engine = create_engine(hana_conn_str)

    in_params = {
        "sqlalchemy_conn": engine.connect(),
        "target_date": "2025-07-09",
        "azure_endpoint": "https://<your-endpoint>.cognitiveservices.azure.com/",
        "azure_key": "<your-azure-key>",
        "output_dir": "./output",
        "preprocessed_dir": "./preprocessed",
        "cropped_dir": "./cropped",
        "ocr_json_dir": "./ocr_json",
        "post_json_dir": "./post_json",
        "error_json_dir": "./error_json",
        "yolo_model_path": "./yolo/best.pt",
        "log_dir": "./logs",
        "logger_name": "WRAPPER",
        "log_level": 20,  # INFO
        "max_workers": 4
    }

    run_wrapper(in_params)
    in_params["sqlalchemy_conn"].close()
