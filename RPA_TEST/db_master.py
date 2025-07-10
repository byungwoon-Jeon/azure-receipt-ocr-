import json
import os
import datetime
import traceback
import logging
from sqlalchemy import text


def query_data_by_date(in_params: dict) -> list:
    """
    SAP HANA 테이블 'LDCOM_CARDFILE_LOG'에서 지정한 날짜의 데이터를 조회

    Args:
        in_params (dict): {
            "sqlalchemy_conn": SQLAlchemy Connection 객체,
            "target_date": str,  # 조회할 날짜 (YYYY-MM-DD 형식), 없으면 어제 날짜
            "logger_name": str,  # 로깅 이름
            "log_level": int     # 로깅 레벨
        }

    Returns:
        list: 조회된 레코드 리스트
    """
    logger = logging.getLogger(in_params.get("logger_name", "query_logger"))
    logger.setLevel(in_params.get("log_level", logging.DEBUG))

    try:
        conn = in_params["sqlalchemy_conn"]

        # 날짜 처리: 입력 없으면 어제로 설정
        target_date = in_params.get("target_date")
        if not target_date:
            target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        query = text("""
            SELECT
                SYSTEM_ID,
                FIID,
                SEQ,
                GUBUN,
                APPR_COMPLT_STD_DATE,
                PROOF_SUM_KRW,
                ATTACH_FILE,
                FILE_PATH,
                LOAD_DATE,
                LOAD_TIME
            FROM
                LDCOM_CARDFILE_LOG
            WHERE
                LOAD_DATE = :target_date
        """)

        result = conn.execute(query, {"target_date": target_date})
        rows = result.fetchall()

        records = [dict(zip(result.keys(), row)) for row in rows]
        logger.info(f"[OK] {target_date} 기준 데이터 {len(records)}건 조회됨")
        return records

    except Exception as e:
        logger.error(f"[ERROR] 데이터 조회 실패: {e}")
        traceback.print_exc()
        return []


def insert_postprocessed_result(json_path: str, in_params: dict) -> None:
    """
    후처리된 JSON 파일을 읽어 SAP HANA DB에 INSERT 수행

    Args:
        json_path (str): 후처리 JSON 파일 경로
        in_params (dict): {
            "sqlalchemy_conn": SQLAlchemy Connection 객체,
            "logger_name": str,  # 로깅 이름
            "log_level": int     # 로깅 레벨
        }
    Returns:
        None
    """
    logger = logging.getLogger(in_params.get("logger_name", "insert_logger"))
    logger.setLevel(in_params.get("log_level", logging.DEBUG))

    if not os.path.exists(json_path):
        logger.error(f"[ERROR] 후처리 JSON 파일이 존재하지 않습니다: {json_path}")
        raise FileNotFoundError(f"후처리 JSON 파일이 존재하지 않습니다: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        summary = data["summary"]
        items = data["items"]

        conn = in_params["sqlalchemy_conn"]

        # 1. INSERT INTO RPA_CCR_LINE_SUMM
        insert_summ_sql = text("""
        INSERT INTO RPA_CCR_LINE_SUMM (
            FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, ATTACH_FILE,
            COUNTRY, RECEIPT_TYPE, MERCHANT_NAME, MERCHANT_PHONE_NO,
            DELIVERY_ADDR, TRANSACTION_DATE, TRANSACTION_TIME,
            TOTAL_AMOUNT, SUMTOTAL_AMOUNT, TAX_AMOUNT, BIZ_NO,
            RESULT_CODE, RESULT_MESSAGE, CREATE_DATE, UPDATE_DATE
        ) VALUES (
            :FIID, :LINE_INDEX, :RECEIPT_INDEX, :COMMON_YN, :ATTACH_FILE,
            :COUNTRY, :RECEIPT_TYPE, :MERCHANT_NAME, :MERCHANT_PHONE_NO,
            :DELIVERY_ADDR, TO_DATE(:TRANSACTION_DATE, 'YYYY-MM-DD'),
            :TRANSACTION_TIME, :TOTAL_AMOUNT, :SUMTOTAL_AMOUNT,
            :TAX_AMOUNT, :BIZ_NO, :RESULT_CODE, :RESULT_MESSAGE,
            TO_DATE(:CREATE_DATE, 'YYYY-MM-DD HH24:MI:SS'),
            TO_DATE(:UPDATE_DATE, 'YYYY-MM-DD HH24:MI:SS')
        )
        """)

        conn.execute(insert_summ_sql, summary)

        # 2. INSERT INTO RPA_CCR_LINE_ITEMS
        insert_item_sql = text("""
        INSERT INTO RPA_CCR_LINE_ITEMS (
            FIID, LINE_INDEX, RECEIPT_INDEX, ITEM_INDEX,
            ITEM_NAME, ITEM_QTY, ITEM_UNIT_PRICE, ITEM_TOTAL_PRICE,
            CONTENTS, COMMON_YN, CREATE_DATE, UPDATE_DATE
        ) VALUES (
            :FIID, :LINE_INDEX, :RECEIPT_INDEX, :ITEM_INDEX,
            :ITEM_NAME, :ITEM_QTY, :ITEM_UNIT_PRICE, :ITEM_TOTAL_PRICE,
            :CONTENTS, :COMMON_YN,
            TO_DATE(:CREATE_DATE, 'YYYY-MM-DD HH24:MI:SS'),
            TO_DATE(:UPDATE_DATE, 'YYYY-MM-DD HH24:MI:SS')
        )
        """)

        for item in items:
            conn.execute(insert_item_sql, item)

        logger.info(f"✅ DB INSERT 성공: {json_path}")

    except Exception as e:
        logger.error(f"❌ DB INSERT 실패: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    import cx_Oracle
    from sqlalchemy import create_engine

    # 테스트용 환경변수
    json_path = "./post_json/post_TEST001_1_1.json"
    dsn = cx_Oracle.makedsn("db_host", 1521, service_name="your_service")
    engine = create_engine(f"oracle+cx_oracle://your_id:your_pw@{dsn}")

    in_params = {
        "sqlalchemy_conn": engine.connect(),
        "logger_name": "test_logger",
        "log_level": logging.DEBUG,
        "target_date": "2025-07-10"  # ← 테스트용 날짜
    }

    # 데이터 조회 테스트
    data = query_data_by_date(in_params)
    print("조회 결과 건수:", len(data))

    # DB INSERT 테스트
    insert_postprocessed_result(json_path, in_params)
    in_params["sqlalchemy_conn"].close()
