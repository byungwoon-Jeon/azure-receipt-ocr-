2. 함수 SDD: insert_postprocessed_result(json_path, duser_input)

[함수 이름]
insert_postprocessed_result

[역할 개요]
post_process.py에서 생성한 후처리 JSON 파일을 읽어 SAP HANA DB에 실제로 INSERT하는 함수이다.

JSON 파일 구조

"summary": RPA_CCR_LINE_SUMM에 1건 삽입할 요약 정보

"items": RPA_CCR_LINE_ITEMS에 N건 삽입할 품목 리스트

처리 내용

JSON 존재 여부 확인

JSON 로드 및 summary/items 추출

RPA_CCR_LINE_SUMM에 summary 1건 INSERT

RPA_CCR_LINE_ITEMS에 items N건 INSERT

conn.commit()으로 트랜잭션 확정

품목 건수에 따라 다른 로그 메시지 출력

[함수 시그니처]
def insert_postprocessed_result(json_path: str, duser_input: dict) -> None:

[입력 파라미터 설명]

json_path (str)

후처리 결과 JSON 파일 경로.

내부에는 반드시 다음 구조가 있어야 한다.
{
"summary": {...},
"items": [ {...}, {...}, ... ]
}

duser_input (dict)

DB 연결 정보를 담은 파라미터 딕셔너리.

필수 키

"sqlalchemy_conn"
· SQLAlchemy Connection 객체 (SAP HANA DB 연결)

[출력 형식]

반환값: None

성공 시

별도의 반환값 없이, 로그에 “DB 저장 완료” 메시지가 출력된다.

실패 시

에러 로그 + traceback 출력

현재 코드에서는 예외를 상위로 re-raise 하지 않고, 함수 내부에서 처리 후 종료

[상세 처리 흐름]

0단계. 로거 설정 및 시작 로그

logger = logging.getLogger("WRAPPER")

logger.info("[시작] insert_postprocessed_result")

1단계. JSON 파일 존재 여부 확인

if not os.path.exists(json_path):

logger.error(f"[ERROR] 후처리 JSON 파일이 존재하지 않습니다: {json_path}")

raise FileNotFoundError("후처리 JSON 파일이 존재하지 않습니다: {json_path}")

존재하지 않는 경우에는 바로 예외 발생(여기서는 re-raise 함)

2단계. JSON 로드 및 summary/items 추출

try 블록 내부:

with open(json_path, "r", encoding="utf-8") as f:
data = json.load(f)

summary = data["summary"]
items = data["items"]
conn = duser_input["sqlalchemy_conn"]

3단계. 요약 정보 INSERT (RPA_CCR_LINE_SUMM)

INSERT SQL (SAP HANA용, TO_DATE 사용 안 함):

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

conn.execute(insert_summ_sql, summary)

summary 딕셔너리의 키와 바인딩 변수(:FIID 등) 이름이 동일해야 한다.

post_process 단계에서 summary를 만들 때, 이 스키마에 맞춰 생성해둔 상태여야 한다.

4단계. 품목 리스트 INSERT (RPA_CCR_LINE_ITEMS)

INSERT SQL:

INSERT INTO RPA_CCR_LINE_ITEMS (
FIID, LINE_INDEX, RECEIPT_INDEX, ITEM_INDEX,
ITEM_NAME, ITEM_QTY, ITEM_UNIT_PRICE, ITEM_TOTAL_PRICE,
CONTENTS, COMMON_YN, CREATE_DATE, UPDATE_DATE
) VALUES (
:FIID, :LINE_INDEX, :RECEIPT_INDEX, :ITEM_INDEX,
:ITEM_NAME, :ITEM_QTY, :ITEM_UNIT_PRICE, :ITEM_TOTAL_PRICE,
:CONTENTS, :COMMON_YN, :CREATE_DATE, :UPDATE_DATE
)

for item in items:
conn.execute(insert_item_sql, item)

item_count = len(items)

item_count에 따라 로그 메시지 분기:

if item_count == 0:

logger.warning(f"[완료] DB 저장 - FIID={summary['FIID']}, RECEIPT_INDEX={summary['RECEIPT_INDEX']} (⚠️ 품목 없음)")

else:

logger.info(f"[완료] DB 저장 - FIID={summary['FIID']}, RECEIPT_INDEX={summary['RECEIPT_INDEX']}, ITEMS_INSERTED={item_count}")

5단계. 트랜잭션 커밋

conn.commit()

요약/품목 INSERT를 하나의 트랜잭션으로 확정한다.

6단계. 예외 처리

except Exception as e:

logger.error(f"[ERROR] DB 저장 실패: {e}")

traceback.print_exc()

별도 rollback 코드는 없으며, HANA/SQLAlchemy 설정에 따라 자동 롤백이 이뤄질 수 있음

finally 개념으로 try/except 이후:

logger.info("[종료] insert_postprocessed_result")

[운영/튜닝 포인트]

JSON 스키마

post_process 단계에서 summary, items를 만들 때
DB 필드명과 바인딩 변수명이 반드시 일치해야 한다.

스키마가 바뀌면 post_process.py와 db_master.py를 동시에 수정해야 한다.

트랜잭션 처리

현재는 요약/품목 INSERT를 하나의 트랜잭션으로 묶어 commit한다.

중간에 에러가 나면 except에서 로그만 남기고 끝이므로,
필요 시 rollback을 명시적으로 추가하거나, 예외를 상위로 re-raise하는 정책으로 바꿀 수 있다.

품목 없는 경우 처리

item_count == 0 일 때도 SUMM은 INSERT되고, 품목은 없는 상태로 저장된다.

로그에 “⚠️ 품목 없음”을 남겨 후속 모니터링 시 구분할 수 있도록 설계되어 있다.

========================================
3. main 테스트 블록 개요 (선택적 설명)

[역할 개요]

단독 실행 시(python db_master.py)

TOML에서 HANA 접속 정보 읽기

SQLAlchemy로 연결 생성

query_data_by_date 테스트

insert_postprocessed_result 테스트

[간단 흐름]

Module_config_dex.toml 로드

tomllib.load로 설정 파싱

"SAP HANA DB" 섹션에서 User, Password, Host, Port 읽음

SQLAlchemy 엔진 및 커넥션 생성

conn_str = f"hdbcli://User:Password@Host:Port"

engine = create_engine(conn_str)

conn = engine.connect()

duser_input 구성

{
"sqlalchemy_conn": conn,
"target_date": "2025-07-10"
}

query_data_by_date 테스트

data = query_data_by_date(duser_input)

조회 건수 및 예시 레코드 출력

insert_postprocessed_result 테스트

test_json_path = "./test_post_json/post_TEST001_1_1.json"

insert_postprocessed_result(test_json_path, duser_input) 호출

conn.close()로 연결 종료