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
    """
    하나의 DB 레코드에 대해 전체 OCR 파이프라인 단계를 실행합니다.
    전처리(다운로드 및 YOLO 크롭), Azure OCR 인식, 후처리 및 DB 저장까지 순차적으로 수행하며, 각 단계의 결과에 따라 오류 시 다음 단계를 건너뜁니다.

    입력:
    - record (dict): 처리할 단일 레코드 (FIID, LINE_INDEX, GUBUN, ATTACH_FILE, FILE_PATH 등 포함).
    - in_params (dict): 파이프라인 실행에 필요한 설정 정보가 담긴 딕셔너리 (DB 연결, 경로, Azure OCR 키 등).

    출력:
    - None: 처리는 부수 효과(파일 저장, DB 입력)로 이루어지며, 함수 자체는 값을 반환하지 않습니다. (오류 발생 시 내부적으로 로그를 기록합니다)
    """
    logger.info(f"[시작] process_single_record - FIID={record.get('FIID')}, LINE_INDEX={record.get('LINE_INDEX')}")
    try:
        # 전처리 단계 실행 (다운로드 + 크롭)
        cropped_list = run_pre_pre_process(in_params, record)

        for cropped in cropped_list:
            if "RESULT_CODE" in cropped:
                logger.warning(f"[SKIP] YOLO 오류 발생: {cropped}")
                continue

            # OCR 실행
            ocr_result = run_azure_ocr(in_params, cropped)
            if ocr_result.get("RESULT_CODE") == "AZURE_ERR":
                logger.warning(f"[SKIP] Azure OCR 오류 발생: {ocr_result}")
                continue

            # 후처리 JSON 경로 구성
            json_path = os.path.join(
                in_params["ocr_json_dir"],
                f"{os.path.splitext(os.path.basename(cropped['file_path']))[0]}.ocr.json"
            )

            # 후처리 실행
            post_json_path = post_process_and_save(
                {**in_params, "postprocess_output_dir": in_params["post_json_dir"]},
                {**cropped, "json_path": json_path, "ATTACH_FILE": record.get("ATTACH_FILE")}
            )

            # DB 저장
            insert_postprocessed_result(post_json_path, in_params)

    except Exception as e:
        logger.error(f"[FATAL] 처리 중 오류 발생 - FIID={record.get('FIID')}: {e}", exc_info=True)
    logger.info(f"[종료] process_single_record - FIID={record.get('FIID')}, LINE_INDEX={record.get('LINE_INDEX')}")

def run_wrapper(in_params: dict):
    """
    지정한 날짜에 해당하는 모든 DB 레코드를 조회하여 OCR 파이프라인을 실행합니다.
    각 레코드를 별도의 스레드로 처리하며, 처리할 레코드가 없으면 함수를 종료합니다.

    입력:
    - in_params (dict): 파이프라인 설정 및 DB 연결 정보를 담은 딕셔너리. (sqlalchemy_conn, target_date 등과 OCR/YOLO 관련 설정 포함)

    출력:
    - None: 처리 완료 후 함수는 아무 값도 반환하지 않습니다. (과정 중 로그로 진행 상황을 기록합니다)
    """
    logger.info("[시작] run_wrapper")
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
    logger.info("[종료] run_wrapper")

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
