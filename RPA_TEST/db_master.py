import json
import os
import logging
import traceback
from sqlalchemy import text
from decimal import Decimal

def query_data_by_date(in_params: dict) -> list:
    """
    지정한 날짜의 SAP HANA 테이블 레코드를 조회하여 반환합니다.
    LDCOM_CARDFILE_LOG 테이블에서 해당 날짜(LOAD_DATE 기준)의 레코드들을 조회하며, 필요한 필드들 (FIID, GUBUN, LINE_INDEX, ATTACH_FILE, FILE_PATH)만 가져옵니다.

    입력:
    - in_params (dict): 조회에 필요한 파라미터. sqlalchemy_conn (데이터베이스 연결 객체)와 optional로 target_date (조회할 기준 날짜, 미지정 시 어제 날짜로 기본 설정)를 포함.

    출력:
    - list: 조회된 레코드 딕셔너리들의 리스트. 각 딕셔너리는 FIID, GUBUN, LINE_INDEX, ATTACH_FILE, FILE_PATH 키를 포함하며, LINE_INDEX는 정수형으로 반환됩니다.
    """
    logger.info("[시작] query_data_by_date")
    try:
        conn = in_params["sqlalchemy_conn"]
        import datetime
        target_date = in_params.get("target_date")
        if not target_date:
            target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

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

        # 키 대문자 변환 + Decimal 변환 처리
        records = []
        for row in rows:
            new_rec = {}
            for key, value in zip(result.keys(), row):
                key = key.upper()
                if key == "LINE_INDEX" and isinstance(value, Decimal):
                    value = int(value)
                new_rec[key] = value
            records.append(new_rec)

        logger.info(f"[완료] {target_date} 기준 데이터 {len(records)}건 조회됨")
        logger.info("[종료] query_data_by_date")
        return records

    except Exception as e:
        logger.error(f"[ERROR] 데이터 조회 실패: {e}")
        traceback.print_exc()
        return []

def insert_postprocessed_result(json_path: str, in_params: dict) -> None:
    """
    후처리 완료된 JSON 파일을 읽어 SAP HANA DB의 요약 및 품목 테이블에 삽입합니다.
    요약 정보는 RPA_CCR_LINE_SUMM 테이블에, 항목 리스트는 RPA_CCR_LINE_ITEMS 테이블에 INSERT합니다.

    입력:
    - json_path (str): 후처리 결과 JSON 파일 경로. 이 파일에는 summary와 items 키가 포함된 JSON 구조여야 합니다.
    - in_params (dict): 데이터베이스 연결 정보 등을 포함한 파라미터 딕셔너리. (sqlalchemy_conn 필수)

    출력:
    - None: DB 삽입 완료 후 반환값이 없습니다. (실패 시 예외를 발생시키며, 로그에 에러를 기록합니다)
    """
    logger = logging.getLogger("WRAPPER")
    logger.info("[시작] insert_postprocessed_result")

    if not os.path.exists(json_path):
        logger.error(f"[ERROR] 후처리 JSON 파일이 존재하지 않습니다: {json_path}")
        raise FileNotFoundError(f"후처리 JSON 파일이 존재하지 않습니다: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        summary = data["summary"]
        items = data["items"]
        conn = in_params["sqlalchemy_conn"]

        # ✅ SAP HANA용 INSERT 문 (TO_DATE 사용하지 않음)
        insert_summ_sql = text("""
            INSERT INTO RPA_CCR_LINE_SUMM (
                FIID, GUBUN, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, ATTACH_FILE,
                COUNTRY, RECEIPT_TYPE, MERCHANT_NAME, MERCHANT_PHONE_NO,
                DELIVERY_ADDR, TRANSACTION_DATE, TRANSACTION_TIME,
                TOTAL_AMOUNT, SUMTOTAL_AMOUNT, TAX_AMOUNT, BIZ_NO,
                RESULT_CODE, RESULT_MESSAGE, CREATE_DATE, UPDATE_DATE
            ) VALUES (
                :FIID, :GUBUN, :LINE_INDEX, :RECEIPT_INDEX, :COMMON_YN, :ATTACH_FILE,
                :COUNTRY, :RECEIPT_TYPE, :MERCHANT_NAME, :MERCHANT_PHONE_NO,
                :DELIVERY_ADDR, :TRANSACTION_DATE, :TRANSACTION_TIME,
                :TOTAL_AMOUNT, :SUMTOTAL_AMOUNT, :TAX_AMOUNT, :BIZ_NO,
                :RESULT_CODE, :RESULT_MESSAGE, :CREATE_DATE, :UPDATE_DATE
            )
        """)
        conn.execute(insert_summ_sql, summary)

        insert_item_sql = text("""
            INSERT INTO RPA_CCR_LINE_ITEMS (
                FIID, LINE_INDEX, RECEIPT_INDEX, ITEM_INDEX,
                ITEM_NAME, ITEM_QTY, ITEM_UNIT_PRICE, ITEM_TOTAL_PRICE,
                CONTENTS, COMMON_YN, CREATE_DATE, UPDATE_DATE
            ) VALUES (
                :FIID, :LINE_INDEX, :RECEIPT_INDEX, :ITEM_INDEX,
                :ITEM_NAME, :ITEM_QTY, :ITEM_UNIT_PRICE, :ITEM_TOTAL_PRICE,
                :CONTENTS, :COMMON_YN, :CREATE_DATE, :UPDATE_DATE
            )
        """)

        for item in items:
            conn.execute(insert_item_sql, item)
        # ✅ 수정 코드 (비어있을 경우 구분해서 출력):
        item_count = len(items)

        if item_count == 0:
            logger.warning(f"[완료] DB 저장 - FIID={summary['FIID']}, RECEIPT_INDEX={summary['RECEIPT_INDEX']} (⚠️ 품목 없음)")
        else:
            logger.info(f"[완료] DB 저장 - FIID={summary['FIID']}, RECEIPT_INDEX={summary['RECEIPT_INDEX']}, ITEMS_INSERTED={item_count}")
        
        conn.commit()

    except Exception as e:
        logger.error(f"[ERROR] DB 저장 실패: {e}")
        traceback.print_exc()

    logger.info("[종료] insert_postprocessed_result")

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
