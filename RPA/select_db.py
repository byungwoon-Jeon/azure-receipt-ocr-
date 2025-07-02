import os
import csv
import traceback
from datetime import datetime, timedelta
from typing import List, Tuple

def select_and_save_csv(in_params: dict, db_config: dict) -> List[Tuple]:
    """
    전날 날짜 기준으로 DB에서 데이터를 SELECT하고 CSV로 저장한 뒤, 리스트로 반환하는 함수

    Args:
        in_params (dict): {
            "csv_output_dir": "CSV 저장 경로 (폴더)",
            ...
        }
        db_config (dict): DB 연결 정보
    Returns:
        List[Tuple]: 조회된 DB 결과 리스트
    """
    try:
        # 1. 전날 날짜 구하기
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 2. 쿼리 구성
        query = """
            SELECT FIID, SEQ, GUBUN, ATTACH_FILE, FILE_PATH, LOAD_DATE
            FROM LDCOM_CARDFILE_LOG
            WHERE TO_CHAR(LOAD_DATE, 'YYYY-MM-DD') = :1
        """

        # 3. DB에서 데이터 조회
        from util.db_utils import manage_db_query  # 공통 유틸 사용
        rows = manage_db_query(query=query, params=(target_date,), db_config=db_config)

        if not rows:
            print("전날 데이터가 존재하지 않습니다.")
            return []

        # 4. CSV 저장 경로 지정
        csv_output_dir = in_params["csv_output_dir"]
        os.makedirs(csv_output_dir, exist_ok=True)

        csv_path = os.path.join(csv_output_dir, f"ldcom_cardfile_log_{target_date}.csv")

        # 5. CSV 저장
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["FIID", "SEQ", "GUBUN", "ATTACH_FILE", "FILE_PATH", "LOAD_DATE"])
            writer.writerows(rows)

        print(f"[INFO] {len(rows)}건의 데이터를 CSV로 저장 완료 → {csv_path}")
        return rows

    except Exception as e:
        print(f"[ERROR] DB 조회 및 CSV 저장 실패: {e}")
        traceback.print_exc()
        return []
