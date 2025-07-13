import os
import json
import logging
import tomllib
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine

from db_master import query_data_by_date, insert_postprocessed_result
from pre_pre_process import run_pre_pre_process    # Integrated pre-processing + YOLO
from doc_process import run_azure_ocr
from post_process import post_process_and_save

def process_single_record(record: dict, in_params: dict):
    """Process a single DB record through the entire OCR pipeline."""
    logger = logging.getLogger("WRAPPER")
    try:
        # Run combined preprocessing (download + YOLO cropping)
        cropped_list = run_pre_pre_process(in_params, record)
        for cropped in cropped_list:
            # Skip further processing if YOLO detected an error for this image
            if "RESULT_CODE" in cropped:
                logger.warning(f"[SKIP] YOLO 오류: {cropped}")
                continue

            # Run Azure OCR on the cropped image
            ocr_result = run_azure_ocr(in_params, cropped)
            if ocr_result.get("RESULT_CODE") == "AZURE_ERR":
                # Skip post-processing if OCR failed for this cropped image
                continue

            # Prepare for post-processing: get OCR JSON file path
            fiid = cropped["FIID"]
            line_index = cropped["LINE_INDEX"]
            receipt_index = cropped["RECEIPT_INDEX"]
            json_path = os.path.join(
                in_params["ocr_json_dir"],
                f"{os.path.splitext(os.path.basename(cropped['file_path']))[0]}.ocr.json"
            )

            # Run post-processing and save results to JSON
            post_json_path = post_process_and_save(
                {**in_params, "postprocess_output_dir": in_params["post_json_dir"]}, 
                {**cropped, "json_path": json_path, "ATTACH_FILE": record.get("ATTACH_FILE")}
            )

            # Insert the results into the SAP HANA database
            insert_postprocessed_result(post_json_path, in_params)
    except Exception as e:
        logger.error(f"[FATAL] Record processing failed: {record}\n{e}")

def run_wrapper(in_params: dict):
    """Run the OCR processing pipeline for all records of the target date."""
    logger = logging.getLogger("WRAPPER")
    # Query records from SAP HANA for the given date
    data_records = query_data_by_date(in_params)
    if not data_records:
        logger.info("📭 처리할 데이터가 없습니다.")  # No data to process
        return

    logger.info(f"총 {len(data_records)}건 처리 시작")  # Starting processing for N records
    max_workers = in_params.get("max_workers", 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single_record, rec, in_params) for rec in data_records]
        for future in as_completed(futures):
            future.result()
    logger.info("✅ 전체 파이프라인 완료")  # Pipeline complete

if __name__ == "__main__":
    # Load database configuration from TOML file
    with open("Module_config_dex.toml", "rb") as f:
        config = tomllib.load(f)
    db_conf = config.get("database", config.get("hana", {}))  # support [database] or [hana] section
    hana_user = db_conf["user"]; hana_pass = db_conf["password"]
    hana_host = db_conf["host"]; hana_port = db_conf["port"]
    hana_conn_str = f"hdbcli://{hana_user}:{hana_pass}@{hana_host}:{hana_port}"
    engine = create_engine(hana_conn_str)

    # Set up unified logging (file + console)
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "pipeline.log")
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("WRAPPER")
    logger.setLevel(logging.INFO)  # Use INFO level or as specified

    # Prepare parameters for pipeline
    in_params = {
        "sqlalchemy_conn": engine.connect(),
        # target_date not provided will default to yesterday in query_data_by_date if needed
        "target_date": "2025-07-09",  # Example date; could be omitted or set as needed
        "azure_endpoint": "https://<your-endpoint>.cognitiveservices.azure.com/",
        "azure_key": "<your-azure-key>",
        "output_dir": "./output",
        "preprocessed_dir": "./preprocessed",
        "cropped_dir": "./cropped",
        "ocr_json_dir": "./ocr_json",
        "post_json_dir": "./post_json",
        "error_json_dir": "./error_json",
        "yolo_model_path": "./yolo/best.pt",
        "max_workers": 4
    }

    # Run the pipeline
    run_wrapper(in_params)

    # Clean up database connection
    in_params["sqlalchemy_conn"].close()
