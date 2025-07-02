import os
import csv
from datetime import datetime, timedelta
from typing import List, Dict

def select_and_save_csv(in_params: dict) -> List[Dict]:
    """
    전날 날짜 기준으로 LDCOM_CARDFILE_LOG 테이블에서 데이터 조회 후,
    CSV로 저장하고 딕셔너리 리스트로 반환

    Args:
        in_params (dict): {
            "db_config": {...},
            "csv_output_dir": "...",
            ...
        }

    Returns:
        List[Dict]: 조회된 데이터의 리스트 (딕셔너리 형태)
    """
    import logging
    from util import idp_utils

    logger = idp_utils.setup_logger("select_and_save_csv", logging.DEBUG)

    # 날짜 계산 (전날 기준)
    today = datetime.now()
    target_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')

    # 쿼리 정의
    query = """
        SELECT 
            FIID, SEQ, GUBUN, ATTACH_FILE, FILE_PATH, LOAD_DATE 
        FROM 
            LDCOM_CARDFILE_LOG 
        WHERE 
            LOAD_DATE = TO_DATE(:1, 'YYYY-MM-DD')
    """

    try:
        # DB 조회
        from util.db_utils import manage_db_query  # ← 회사 유틸 사용
        rows = manage_db_query(query, (target_date,), db_config=in_params["db_config"])
        
        if not rows:
            logger.warning("전날 데이터 없음")
            return []

        # 저장 디렉토리 확인
        os.makedirs(in_params["csv_output_dir"], exist_ok=True)
        csv_path = os.path.join(in_params["csv_output_dir"], f"cardfile_log_{target_date}.csv")

        # 컬럼 이름 정의
        col_names = ["FIID", "SEQ", "GUBUN", "ATTACH_FILE", "FILE_PATH", "LOAD_DATE"]

        # CSV 저장
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            writer.writerows(rows)

        logger.info(f"CSV 저장 완료: {csv_path}")

        # 리스트 of 딕셔너리로 변환
        dict_list = [
            dict(zip(col_names, row))
            for row in rows
        ]

        return dict_list

    except Exception as e:
        logger.error(f"[select_and_save_csv] 오류 발생: {e}")
        return []
