함수 SDD: post_process_and_save (post_process.py)
========================================

[함수 이름]
post_process_and_save

[역할 개요]
Azure OCR 결과(JSON)를 읽어서

요약 정보(summary)와

품목 리스트(items)를 추출한 뒤,
DB insert에 바로 쓸 수 있는 구조로 재가공하여
summary, items 두 개의 키를 가진 JSON 파일로 저장하는 후처리(post-processing) 함수이다. 

post_process

정상 처리 시에는

RESULT_CODE = 200, RESULT_MESSAGE = "SUCCESS"
를 포함한 summary를 만들고, 품목 데이터는 item_list로 구성한다.

오류가 발생하면:

에러 내용을 담은 summary + 빈 items 리스트 형태의 JSON을 별도 경로에 저장하고,

그 에러 JSON 파일 경로를 반환한다.

[함수 시그니처]
def post_process_and_save(duser_input: dict, record: dict) -> str:

[입력 파라미터 설명]

duser_input (dict)

후처리 동작에 필요한 설정값 및 경로 정보가 들어있는 딕셔너리.

필수 키:
· "postprocess_output_dir": 후처리 결과 JSON을 저장할 디렉터리 경로

선택 키:
· "error_json_dir": 오류 발생 시 에러 JSON을 저장할 디렉터리 경로 (기본값: "./error_json")

record (dict)

특정 한 장의 OCR 결과에 대한 후처리 대상 정보를 담은 딕셔너리.

필수 키:
· "json_path" : Azure OCR 결과 JSON(.ocr.json) 파일 경로
· "FIID" : 원본 레코드 식별자
· "LINE_INDEX" : 원본 라인 인덱스
· "RECEIPT_INDEX": 영수증 순번
· "COMMON_YN" : 공통 여부 플래그

선택 키:
· "GUBUN" : 구분 값
· "ATTACH_FILE" : 원본 첨부 URL/파일 경로 (요약에 함께 넣기 위함)

[출력 형식]

반환값: str

정상 처리 시:
· 생성된 후처리 결과 JSON 파일 경로
· 파일 내부 구조:
{
"summary": {...},
"items": [...]
}

오류 발생 시:
· 생성된 “실패용 후처리 JSON” 파일 경로
· 내부 구조:
{
"summary": { RESULT_CODE="POST_ERR", RESULT_MESSAGE="<에러 메시지>", ... },
"items": []
}

[상세 처리 흐름]

1단계. 필수 입력값 검사 및 디렉터리 준비

duser_input에 "postprocess_output_dir" 키가 있는지 assert로 확인한다.

record에 "json_path", "FIID", "LINE_INDEX", "RECEIPT_INDEX", "COMMON_YN" 키가 있는지 assert로 확인한다.

output_dir = duser_input["postprocess_output_dir"]

os.makedirs(output_dir, exist_ok=True)로 결과 디렉터리를 생성(없으면 생성, 있으면 그대로 사용).

json_path = record["json_path"]

해당 파일이 존재하는지 검사한다.
· 존재하지 않으면 FileNotFoundError를 발생시킨다.

2단계. OCR JSON 파일 로드 및 필드 추출

with open(json_path, "r", encoding="utf-8")로 JSON을 읽어서 data에 로드한다.

Azure OCR 결과 구조에서:
· doc = data.get("analyzeResult", {}).get("documents", [{}])[0]
· fields = doc.get("fields", {}) (doc가 dict인 경우에만)

현재 시간 now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")를 생성한다.

record에서 FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, GUBUN, ATTACH_FILE 값을 가져온다.

3단계. summary 딕셔너리 구성

summary 구조는 DB 테이블 RPA_CCR_LINE_SUMM에 바로 매핑할 수 있도록 구성된다.

주요 필드 매핑:
· "FIID" : record["FIID"]
· "LINE_INDEX" : record["LINE_INDEX"]
· "RECEIPT_INDEX": record["RECEIPT_INDEX"]
· "COMMON_YN" : record["COMMON_YN"]
· "GUBUN" : record.get("GUBUN")
· "ATTACH_FILE" : record.get("ATTACH_FILE")
· "COUNTRY" : fields["CountryRegion"]["valueCountryRegion"]
· "RECEIPT_TYPE" : fields["MerchantCategory"]["valueString"]
· "MERCHANT_NAME": fields["MerchantName"]["valueString"]
· "MERCHANT_PHONE_NO": fields["MerchantPhoneNumber"]["valueString"]
· "DELIVERY_ADDR": 현재는 None (추후 필요 시 추가 매핑 가능)
· "TRANSACTION_DATE": fields["TransactionDate"]["valueDate"]
· "TRANSACTION_TIME": fields["TransactionTime"]["valueTime"]
· "TOTAL_AMOUNT" : str(fields["Total"]["valueCurrency"]["amount"])
· "SUMTOTAL_AMOUNT" : str(fields["Subtotal"]["valueCurrency"]["amount"])
· "TAX_AMOUNT" : str(fields["TotalTax"]["valueCurrency"]["amount"])
· "BIZ_NO" : 현재는 None (필요시 별도 추출 가능)
· "RESULT_CODE" : 200
· "RESULT_MESSAGE" : "SUCCESS"
· "CREATE_DATE" : now_str
· "UPDATE_DATE" : now_str

각 필드 접근은 .get을 사용해 값이 없을 경우 None이 되도록 방어적으로 작성되어 있다.

4단계. 라인 아이템(items) 추출

item_list = []

items_field = fields.get("Items", {})

items_field가 dict이고, "valueArray" 키를 가진 경우에만 반복 처리한다.
· for idx, item in enumerate(items_field["valueArray"], start=1):
- obj = item.get("valueObject", {}) if item else {}
- item_list.append({
"FIID": fiid,
"LINE_INDEX": line_index,
"RECEIPT_INDEX": receipt_index,
"ITEM_INDEX": idx,
"ITEM_NAME": obj["Description"]["valueString"],
"ITEM_QTY": str(obj["Quantity"]["valueNumber"]) if Quantity 필드가 있으면,
"ITEM_UNIT_PRICE": str(obj["Price"]["valueCurrency"]["amount"]) if Price 필드가 있으면,
"ITEM_TOTAL_PRICE": str(obj["TotalPrice"]["valueCurrency"]["amount"]) if TotalPrice 필드가 있으면,
"CONTENTS": obj 전체를 json.dumps로 문자열화한 값,
"COMMON_YN": common_yn,
"CREATE_DATE": now_str,
"UPDATE_DATE": now_str
})

이 리스트는 DB 테이블 RPA_CCR_LINE_ITEMS에 그대로 매핑할 수 있는 구조이다.

5단계. 후처리 결과 JSON 저장

result_json = {"summary": summary, "items": item_list}

output_filename = f"{fiid}{line_index}{receipt_index}_post.json"

output_path = os.path.join(output_dir, output_filename)

with open(output_path, "w", encoding="utf-8") as out_f:
json.dump(result_json, out_f, ensure_ascii=False, indent=2)

로그로 “[완료] 후처리 결과 저장: {output_path}”를 남기고,

output_path를 반환한다.

6단계. 예외 처리 흐름

전체 로직은 try/except로 감싸져 있으며, 예외가 발생하면:
· 에러 로그 기록
· traceback.print_exc()로 스택 트레이스 출력
· error_json_dir = duser_input.get("error_json_dir", "./error_json")
· error_path = "<error_json_dir>/fail_{FIID}_{LINE_INDEX}.json"
· 디렉터리가 없으면 os.makedirs로 생성

에러 발생 시 저장하는 JSON 구조:
· now_str = 현재 시각
· error_summary = {
"FIID": record.get("FIID"),
"LINE_INDEX": record.get("LINE_INDEX"),
"RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
"COMMON_YN": record.get("COMMON_YN"),
"GUBUN": record.get("GUBUN"),
"ATTACH_FILE": record.get("ATTACH_FILE"),
"COUNTRY": None,
"RECEIPT_TYPE": None,
"MERCHANT_NAME": None,
"MERCHANT_PHONE_NO": None,
"DELIVERY_ADDR": None,
"TRANSACTION_DATE": None,
"TRANSACTION_TIME": None,
"TOTAL_AMOUNT": None,
"SUMTOTAL_AMOUNT": None,
"TAX_AMOUNT": None,
"BIZ_NO": None,
"RESULT_CODE": "POST_ERR",
"RESULT_MESSAGE": str(e),
"CREATE_DATE": now_str,
"UPDATE_DATE": now_str
}

· error_json 내용: {"summary": error_summary, "items": []}
· 이 에러 JSON 파일 경로(error_path)를 반환한다.

========================================
2. 함수 SDD: insert_postprocessed_result (db_master.py)

[함수 이름]
insert_postprocessed_result

[역할 개요]
post_process_and_save에서 생성한 후처리 결과 JSON 파일을 읽어서,

요약 정보(summary)를 SAP HANA 테이블 RPA_CCR_LINE_SUMM에 INSERT하고,

품목 리스트(items)를 RPA_CCR_LINE_ITEMS에 다건 INSERT 한 뒤,
commit까지 수행하는 DB 마스터 함수이다. 

db_master

정상 처리 시에는 별도의 반환값 없이 DB에 데이터가 반영되며,
오류 발생 시 에러 로그를 남기고 스택 트레이스를 출력한 뒤 함수를 종료한다.

[함수 시그니처]
def insert_postprocessed_result(json_path: str, duser_input: dict) -> None:

[입력 파라미터 설명]

json_path (str)

post_process_and_save에서 생성한 후처리 결과 JSON 파일 경로.

이 파일 구조는 다음과 같다:
{
"summary": { ... },
"items": [ {...}, {...}, ... ]
}

duser_input (dict)

DB 연결 정보를 포함한 파라미터 딕셔너리.

필수 키:
· "sqlalchemy_conn": SQLAlchemy Connection 객체 (SAP HANA DB 연결)

[출력 형식]

반환값: None

DB INSERT 작업 완료 후 반환값은 없다.

실패 시 예외를 발생시키거나 로그만 남기고 리턴한다(코드에 따라 처리).

[상세 처리 흐름]

1단계. 로그 및 파일 존재 여부 체크

logger = logging.getLogger("WRAPPER")

logger.info("[시작] insert_postprocessed_result")

if not os.path.exists(json_path):
· 에러 로그 출력 후 FileNotFoundError를 발생시킨다.
· 메시지: "후처리 JSON 파일이 존재하지 않습니다: {json_path}"

2단계. JSON 파일 로드 및 summary/items 분리

with open(json_path, "r", encoding="utf-8") as f:
data = json.load(f)

summary = data["summary"]

items = data["items"]

conn = duser_input["sqlalchemy_conn"]

3단계. 요약 정보 INSERT (RPA_CCR_LINE_SUMM)

SAP HANA용 INSERT 문을 text(...)로 정의:
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
· summary 딕셔너리의 키와 바인딩 변수 이름이 일치해야 한다.
· post_process_and_save에서 구성한 summary 구조를 그대로 사용 가능.

4단계. 품목 리스트 INSERT (RPA_CCR_LINE_ITEMS)

INSERT 문 정의:
INSERT INTO RPA_CCR_LINE_ITEMS (
FIID, LINE_INDEX, RECEIPT_INDEX, ITEM_INDEX,
ITEM_NAME, ITEM_QTY, ITEM_UNIT_PRICE, ITEM_TOTAL_PRICE,
CONTENTS, COMMON_YN, CREATE_DATE, UPDATE_DATE
) VALUES (
:FIID, :LINE_INDEX, :RECEIPT_INDEX, :ITEM_INDEX,
:ITEM_NAME, :ITEM_QTY, :ITEM_UNIT_PRICE, :ITEM_TOTAL_PRICE,
:CONTENTS, :COMMON_YN, :CREATE_DATE, :UPDATE_DATE
)

items 리스트를 순회하면서 각 item에 대해 conn.execute(insert_item_sql, item)을 호출한다.

item_count = len(items)

품목 개수에 따라 다른 로그 메시지를 출력한다.
· item_count == 0 인 경우:
logger.warning("[완료] DB 저장 - FIID={FIID}, RECEIPT_INDEX={RECEIPT_INDEX} (⚠️ 품목 없음)")
· item_count > 0 인 경우:
logger.info("[완료] DB 저장 - FIID={FIID}, RECEIPT_INDEX={RECEIPT_INDEX}, ITEMS_INSERTED={item_count}")

5단계. 트랜잭션 커밋

conn.commit()을 호출하여 SUMM/ITEMS 테이블에 대한 INSERT 작업을 확정한다.

6단계. 예외 처리

전체 INSERT 로직은 try/except로 감싸져 있다.

except Exception as e:
· logger.error("[ERROR] DB 저장 실패: {e}")
· traceback.print_exc()
· (필요 시 상위로 예외를 다시 던지거나, 여기서만 로깅하고 끝낼 수 있음. 현재 코드는 로깅 후 함수 종료.)

마지막으로 logger.info("[종료] insert_postprocessed_result")를 출력하며 함수가 종료된다.

이렇게 하면

YOLO 크롭 SDD

(이미 있는 DOC Processing SDD)

post_process_and_save SDD

insert_postprocessed_result SDD

까지 한 줄 흐름으로 연결해서 설명할 수 있을 거야.
필요하면 doc_process(run_azure_ocr)도 같은 스타일로 다시 뽑아줄게.