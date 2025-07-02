from datetime import datetime, timedelta
from util import db_utils  # manage_db_query 함수가 정의된 모듈
import logging

logger = logging.getLogger(__name__)

def get_yesterday_cardfile_data(db_config: dict) -> list:
    """
    LDCOM_CARDFILE_LOG 테이블에서 전날(어제) 기준의 데이터 조회

    Args:
        db_config (dict): DB 연결 정보 (host, port, service_name, user, password)

    Returns:
        list: 조회된 행의 리스트 (FIID, SEQ, ATTACH_FILE, FILE_PATH, LOAD_DATE)
              예외 발생 시 빈 리스트 반환
    """
    try:
        # 전날 날짜 계산
        yesterday = datetime.today() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')

        # 쿼리 정의
        query = """
            SELECT FIID, SEQ, ATTACH_FILE, FILE_PATH, LOAD_DATE
            FROM LDCOM_CARDFILE_LOG
            WHERE TRUNC(LOAD_DATE) = TO_DATE(:1, 'YYYY-MM-DD')
        """

        # DB 조회 실행
        rows = db_utils.manage_db_query(query=query, params=(date_str,), db_config=db_config)

        if rows is None:
            logger.warning("DB 조회 결과가 None입니다.")
            return []

        logger.info(f"{len(rows)}건의 전날 데이터를 조회했습니다.")
        return rows

    except Exception as e:
        logger.exception(f"전날 카드파일 데이터를 조회하는 중 오류 발생: {e}")
        return []