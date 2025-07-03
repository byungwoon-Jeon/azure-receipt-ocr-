import os
import csv
import datetime
from pathlib import Path
import oracledb  # Oracle DB 모듈
import logging

logger = logging.getLogger("DB_QUERY")
logger.setLevel(logging.DEBUG)


def validate_required_fields(in_params: dict) -> dict:
    """
    in_params에 필요한 필드들이 모두 존재하는지 검증
    """
    required_fields = ["db_config", "csv_output_dir"]
    db_required_fields = ["user", "password", "host", "port", "service_name"]

    missing_fields = []

    for field in required_fields:
        if field not in in_params:
            missing_fields.append(field)

    if "db_config" in in_params:
        for db_field in db_required_fields:
            if db_field not in in_params["db_config"]:
                missing_fields.append(f"db_config.{db_field}")

    if missing_fields:
        return {
            "has_error": True,
            "error_fields": missing_fields,
            "error_message": "필수 입력값이 누락되었습니다."
        }

    return {"has_error": False}


def query_yesterday_data(in_params: dict) -> list:
    """
    어제 날짜 기준으로 Oracle DB에서 데이터를 조회하고, 리스트와 CSV로 반환

    Returns:
        List[dict]: [{FIID, LINE_INDEX, ATTACH_FILE, FILE_PATH, COMMON_YN}, ...]
    """
    try:
        # ─ 1. 입력값 검증
        validation = validate_required_fields(in_params)
        if validation["has_error"]:
            logger.error(f"[DB] 입력값 누락: {validation['error_fields']}")
            return []

        # ─ 2. 설정 추출
        db_config = in_params["db_config"]
        output_dir = Path(in_params["csv_output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        # ─ 3. 쿼리 수행
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d")
        query = """
            SELECT FIID, SEQ AS LINE_INDEX, ATTACH_FILE, FILE_PATH
            FROM LDCOM_CARDFILE_LOG
            WHERE LOAD_DATE = :1
        """

        dsn = f"{db_config['host']}:{db_config['port']}/{db_config['service_name']}"
        conn = oracledb.connect(user=db_config["user"], password=db_config["password"], dsn=dsn)
        cursor = conn.cursor()
        cursor.execute(query, (yesterday,))
        rows = cursor.fetchall()

        # ─ 4. 결과 정리
        result = []
        for row in rows:
            fiid, line_index, attach_file, file_path = row
            result.append({
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "ATTACH_FILE": attach_file,
                "FILE_PATH": file_path,
                "COMMON_YN": "Y" if file_path else "N"
            })

        # ─ 5. CSV 저장
        csv_path = output_dir / f"query_result_{yesterday}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["FIID", "LINE_INDEX", "ATTACH_FILE", "FILE_PATH", "COMMON_YN"])
            writer.writeheader()
            writer.writerows(result)

        logger.info(f"[DB] 어제 데이터 {len(result)}건 조회 완료. CSV 저장 경로: {csv_path}")
        return result

    except Exception as e:
        logger.error(f"[DB] 전날 데이터 조회 중 오류 발생: {e}")
        return []

from util import idp_utils

in_params = {
    "logger": idp_utils.setup_logger("QUERY_LOGGER", logging.DEBUG),
    "connection": conn,  # HANA DB 연결 객체
    "input_table": "LDCOM_CARDFILE_LOG",
    "load_date_column": "LOAD_DATE"
}

df = query_yesterday_data(in_params)
