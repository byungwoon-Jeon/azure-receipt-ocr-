함수 SDD: run_azure_ocr (doc_process.py)
========================================

[함수 이름]
run_azure_ocr

[역할 개요]
Azure Form Recognizer(Document Intelligence)의 prebuilt-receipt 모델을 호출하여
record["file_path"]에 해당하는 영수증 이미지를 OCR 처리하고,

Azure SDK가 반환한 OCR 결과를 dict 형태로 얻은 뒤

그 결과를 <원본파일명>.ocr.json 형식의 파일로 저장하고

그 dict를 그대로 호출 측에 반환하는 함수이다.

오류가 발생할 경우에는,

에러 내용을 담은 JSON 파일(fail_*.json)을 별도 폴더에 생성하고,

RESULT_CODE="AZURE_ERR"와 에러 메시지, 그리고 식별자(FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, GUBUN)를 포함한 딕셔너리를 반환한다.

즉, 이 함수는 “크롭된 영수증 이미지 → Azure OCR → .ocr.json 저장”까지의 Doc Processing 단계를 담당한다.

[함수 시그니처]
def run_azure_ocr(duser_input: dict, record: dict) -> dict:

[입력 파라미터 설명]

duser_input (dict)
Azure OCR 실행에 필요한 설정 값들을 담는 딕셔너리.

필수 키

"azure_endpoint"
· Azure Form Recognizer 리소스의 엔드포인트 URL
· 예: "https://<리소스이름>.cognitiveservices.azure.com/"

"azure_key"
· 해당 리소스에 접근하기 위한 API 키 (Primary / Secondary Key)

"ocr_json_dir"
· OCR 결과 JSON(.ocr.json)을 저장할 디렉터리 경로
· 없으면 함수 내부에서 os.makedirs로 생성한다.

선택 키

"error_json_dir"
· OCR 호출 실패 시 에러 JSON을 저장할 디렉터리 경로
· 지정되지 않으면 기본값 "./error_json" 사용

record (dict)
OCR 대상 이미지 및 식별 정보를 담고 있는 딕셔너리.

필수 키

"file_path"
· OCR을 수행할 입력 이미지 파일 경로 (크롭된 영수증 PNG 등)

선택(그러나 상위 파이프라인에서는 사실상 필수로 사용하는) 키

"FIID" : 원본 레코드 식별자

"LINE_INDEX" : 원본 라인 인덱스

"RECEIPT_INDEX": 영수증 순번

"COMMON_YN" : 공통 여부 플래그

"GUBUN" : 구분 값 (ATTACH/FILE_PATH 등)

[출력 형식]

반환값: dict

정상 처리(성공) 시

Azure Form Recognizer의 AnalyzeResult 객체를 to_dict()로 변환한 결과 딕셔너리.

구조 예시(간략화):
{
"modelId": "prebuilt-receipt",
"content": "...",
"pages": [...],
"documents": [...],
"tables": [...],
...
}

이 딕셔너리 자체에는 FIID 등 식별자는 포함되지 않으며,
실제 후속 단계(post_process)는 이 함수가 저장한 .ocr.json 파일을 기준으로 진행한다.

예외(실패) 시

다음과 같은 구조의 딕셔너리 반환:
{
"FIID": record.get("FIID"),
"LINE_INDEX": record.get("LINE_INDEX"),
"RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
"COMMON_YN": record.get("COMMON_YN"),
"GUBUN": record.get("GUBUN"),
"RESULT_CODE": "AZURE_ERR",
"RESULT_MESSAGE": f"OCR 실패: {에러메시지}"
}

동시에 error_json_dir 아래에 fail_{FIID}_{LINE_INDEX}_{RECEIPT_INDEX}_{COMMON_YN}.json 형식의 에러 JSON 파일을 생성한다.

[상세 처리 흐름]

1단계. 로거 및 시작 로그

전역에서 logger = logging.getLogger("AZURE_OCR")를 사용한다.

함수 시작 시:

logger.info("[시작] run_azure_ocr")

2단계. 필수 설정값 및 입력값 검증

try 블록 내에서 assert를 사용해 필수 키를 검증한다.

assert "azure_endpoint" in duser_input, "'azure_endpoint'가 duser_input에 없습니다."

assert "azure_key" in duser_input, "'azure_key'가 duser_input에 없습니다."

assert "ocr_json_dir" in duser_input, "'ocr_json_dir'가 duser_input에 없습니다."

assert "file_path" in record, "'file_path'가 record에 없습니다."

이 중 하나라도 없으면 AssertionError가 발생하여 except 블록으로 흐름이 이동한다.

3단계. Azure 클라이언트 및 폴더 준비

endpoint = duser_input["azure_endpoint"]

key = duser_input["azure_key"]

json_dir = duser_input["ocr_json_dir"]

os.makedirs(json_dir, exist_ok=True)
· OCR 결과 JSON 파일을 저장할 폴더가 없으면 새로 생성한다.

file_path = record["file_path"]

Azure SDK 클라이언트 생성:

client = DocumentAnalysisClient(
endpoint=endpoint,
credential=AzureKeyCredential(key)
)

4단계. Azure Form Recognizer 호출 (prebuilt-receipt)

with open(file_path, "rb") as f:
poller = client.begin_analyze_document("prebuilt-receipt", document=f)
result = poller.result()
result_dict = result.to_dict()

여기서 사용되는 모델 ID는 "prebuilt-receipt"이며, 영수증 특화 모델이다.

poller.result()가 반환하는 객체는 AnalyzeResult이며, 이를 dict로 변환해 result_dict로 보관한다.

5단계. OCR 결과 JSON 파일 저장

base_filename = os.path.splitext(os.path.basename(file_path))[0]
· 예: file_path=".../abc_123_r1.png" → base_filename="abc_123_r1"

json_filename = f"{base_filename}.ocr.json"
· 예: "abc_123_r1.ocr.json"

json_path = os.path.join(json_dir, json_filename)

with open(json_path, "w", encoding="utf-8") as jf:
json.dump(result_dict, jf, ensure_ascii=False, indent=2)

logger.info(f"[완료] OCR 성공 및 JSON 저장: {json_path}")

6단계. 정상 종료 처리

logger.info("[종료] run_azure_ocr")

return result_dict
· 이 반환값은 크게 “즉시 후속 로직에서 참조하거나, 테스트 용”으로 사용할 수 있고,
실제 후처리(post_process)는 json_path에 저장된 파일을 기준으로 동작한다.

[예외 / 오류 처리 흐름]

예외 발생 시 공통 처리

except Exception as e: 블록에서 다음을 수행한다.

logger.error(f"[ERROR] OCR 실패: {e}")

traceback.print_exc()

에러 JSON 저장

error_json_dir = duser_input.get("error_json_dir", "./error_json")

os.makedirs(error_json_dir, exist_ok=True)

fail_filename 패턴:

fail_filename = f"fail_{record.get('FIID')}{record.get('LINE_INDEX')}{record.get('RECEIPT_INDEX')}_{record.get('COMMON_YN')}.json"
(코드 상에서는 중간에 ...가 있지만 의도는 위와 같은 형태)

fail_path = os.path.join(error_json_dir, fail_filename)

with open(fail_path, "w", encoding="utf-8") as f:
json.dump({
"RESULT_CODE": "AZURE_ERR",
"RESULT_MESSAGE": f"OCR 실패: {str(e)}",
"FIID": record.get("FIID"),
"LINE_INDEX": record.get("LINE_INDEX"),
"RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
"COMMON_YN": record.get("COMMON_YN"),
"GUBUN": record.get("GUBUN")
}, f, ensure_ascii=False, indent=2)

에러 딕셔너리 반환

logger.info("[종료] run_azure_ocr (오류로 종료)")

return {
"FIID": record.get("FIID"),
"LINE_INDEX": record.get("LINE_INDEX"),
"RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
"COMMON_YN": record.get("COMMON_YN"),
"GUBUN": record.get("GUBUN"),
"RESULT_CODE": "AZURE_ERR",
"RESULT_MESSAGE": f"OCR 실패: {e}"
}

상위 호출부(예: wrapper.py)에서는

RESULT_CODE를 확인하여 성공/실패를 구분하고,

실패 시 이후 post_process, DB insert를 건너뛰는 식으로 정책을 적용할 수 있다.

[튜닝/운영 관점 포인트]

azure_endpoint / azure_key
· 운영/개발 환경별로 다른 값을 쓰게 될 가능성이 크므로,
duser_input을 통해 외부 설정에서 주입하는 현재 구조가 적절하다.

ocr_json_dir / error_json_dir
· 로그 및 장애 분석을 위해 반드시 별도의 경로를 유지하는 것이 좋다.
· 파일 수가 많아질 수 있으므로, 주기적으로 정리하는 배치나 정책을 별도로 두는 것이 바람직하다.

prebuilt-receipt 모델 버전
· 현재는 단순히 "prebuilt-receipt" 문자열을 사용하고 있으며,
모델 버전 업그레이드가 필요할 경우 이 부분만 교체하면 된다.
· (예: "prebuilt-receipt;2024-07-31" 와 같은 버전 명시 방식)

이 블록 그대로 txt에 복붙해서

YOLO 크롭 SDD

run_azure_ocr SDD

post_process_and_save SDD

insert_postprocessed_result SDD