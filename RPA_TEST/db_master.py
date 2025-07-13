import json
import os
import logging
import traceback
from sqlalchemy import text

def query_data_by_date(in_params: dict) -> list:
    """
    Query the SAP HANA table (e.g., LDCOM_CARDFILE_LOG) for records on the target date.
    Only the necessary fields (FIID, GUBUN, LINE_INDEX, ATTACH_FILE, FILE_PATH) are retrieved.
    """
    logger = logging.getLogger("WRAPPER")
    try:
        conn = in_params["sqlalchemy_conn"]
        # Determine target date (default to yesterday if not provided)
        import datetime
        target_date = in_params.get("target_date")
        if not target_date:
            target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        # Select only the required fields, aliasing SEQ as LINE_INDEX
        query = text("""
            SELECT 
                FIID,
                GUBUN,
                SEQ AS LINE_INDEX,
                ATTACH_FILE,
                FILE_PATH
            FROM LDCOM_CARDFILE_LOG
            WHERE LOAD_DATE = :target_date
        """)
        result = conn.execute(query, {"target_date": target_date})
        rows = result.fetchall()
        # Convert each row to dict
        records = [dict(zip(result.keys(), row)) for row in rows]
        logger.info(f"[OK] {target_date} 기준 데이터 {len(records)}건 조회됨")
        return records
    except Exception as e:
        logger.error(f"[ERROR] 데이터 조회 실패: {e}")
        traceback.print_exc()
        return []

def insert_postprocessed_result(json_path: str, in_params: dict) -> None:
    """
    Read the post-processed JSON file and insert its contents into the SAP HANA tables.
    Inserts into RPA_CCR_LINE_SUMM (including GUBUN) and RPA_CCR_LINE_ITEMS.
    """
    logger = logging.getLogger("WRAPPER")
    if not os.path.exists(json_path):
        logger.error(f"[ERROR] 후처리 JSON 파일이 존재하지 않습니다: {json_path}")
        raise FileNotFoundError(f"후처리 JSON 파일이 존재하지 않습니다: {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        summary = data["summary"]
        items = data["items"]

        conn = in_params["sqlalchemy_conn"]
        # 1. Insert summary line (RPA_CCR_LINE_SUMM), including GUBUN
        insert_summ_sql = text(f"""
            INSERT INTO RPA_CCR_LINE_SUMM (
                FIID, GUBUN, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, ATTACH_FILE,
                COUNTRY, RECEIPT_TYPE, MERCHANT_NAME, MERCHANT_PHONE_NO,
                DELIVERY_ADDR, TRANSACTION_DATE, TRANSACTION_TIME,
                TOTAL_AMOUNT, SUMTOTAL_AMOUNT, TAX_AMOUNT, BIZ_NO,
                RESULT_CODE, RESULT_MESSAGE, CREATE_DATE, UPDATE_DATE
            ) VALUES (
                :FIID, :GUBUN, :LINE_INDEX, :RECEIPT_INDEX, :COMMON_YN, :ATTACH_FILE,
                :COUNTRY, :RECEIPT_TYPE, :MERCHANT_NAME, :MERCHANT_PHONE_NO,
                :DELIVERY_ADDR, TO_DATE(:TRANSACTION_DATE, 'YYYY-MM-DD'),
                :TRANSACTION_TIME, :TOTAL_AMOUNT, :SUMTOTAL_AMOUNT,
                :TAX_AMOUNT, :BIZ_NO, :RESULT_CODE, :RESULT_MESSAGE,
                TO_DATE(:CREATE_DATE, 'YYYY-MM-DD HH24:MI:SS'),
                TO_DATE(:UPDATE_DATE, 'YYYY-MM-DD HH24:MI:SS')
            )
        """)
        conn.execute(insert_summ_sql, summary)

        # 2. Insert each item line (RPA_CCR_LINE_ITEMS)
        insert_item_sql = text(f"""
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

# (No __main__ testing code, as Oracle support is removed and HANA usage is configured in wrapper)
if __name__ == "__main__":
    import tomllib
    from sqlalchemy import create_engine

    # ✅ TOML에서 DB 접속 정보 불러오기
    with open("Module_config_dex.toml", "rb") as f:
        config = tomllib.load(f)
    hana_conf = config.get("SAP HANA DB")

    # ✅ SQLAlchemy 연결 생성
    conn_str = f"hdbcli://{hana_conf['User']}:{hana_conf['Password']}@{hana_conf['Host']}:{hana_conf['Port']}"
    engine = create_engine(conn_str)
    conn = engine.connect()

    in_params = {
        "sqlalchemy_conn": conn,
        "target_date": "2025-07-10",  # 테스트 날짜
    }

    # ✅ 1. 조회 테스트
    print("🔍 query_data_by_date() 테스트")
    data = query_data_by_date(in_params)
    print(f"조회된 건수: {len(data)}")
    if data:
        print("예시 레코드:", data[0])

    # ✅ 2. INSERT 테스트
    print("\n📝 insert_postprocessed_result() 테스트")
    try:
        test_json_path = "./test_post_json/post_TEST001_1_1.json"  # 실제 파일 경로로 교체
        insert_postprocessed_result(test_json_path, in_params)
        print("✅ INSERT 테스트 성공")
    except Exception as e:
        print("❌ INSERT 테스트 실패:", e)

    conn.close()
