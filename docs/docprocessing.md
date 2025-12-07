📄 Doc-processing Module – Software Design Document (SDD)

Version 1.0 — Markdown Edition

# 1. Module Overview
## 1.1 Purpose

Doc-processing 모듈은 Pre-processing 단계에서 준비된 Crop 이미지를 기반으로 Azure Form Recognizer OCR 서비스를 호출하여 구조화된 OCR 결과(JSON) 를 생성하는 기능을 담당한다.

이 단계에서 수행하는 핵심 목적은 다음과 같다:

Azure Form Recognizer(“prebuilt-receipt” 모델) 호출

OCR 결과를 JSON 구조로 변환하여 저장

OCR 실패 시 오류 JSON 생성

상위 단계(Post-processing)에서 사용할 데이터 구조 제공

즉, 이 모듈은 “이미지 → OCR 데이터(JSON)”를 만드는 핵심 OCR 엔진 호출 담당자이다.

# 1.2 Responsibilities

Azure OCR API 호출

OCR 결과(JSON) 저장

OCR 실패 시 오류 JSON 생성 및 에러 구조 반환

결과를 Python dict로 상위 모듈에 전달

FIID / LINE_INDEX / RECEIPT_INDEX / COMMON_YN 등 파이프라인 식별자 보존

# 1.3 Inputs
Key	Type	Description
duser_input	dict	Azure endpoint, key, JSON 저장 경로 등 설정값
record	dict	file_path, FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN 등 OCR 대상 정보
# 1.4 Outputs
성공 시

Azure OCR의 전체 결과(JSON)를 Python dict 형태로 반환하며, 파일로도 저장한다.

예:

{
  "analyzeResult": {
    "documents": [
      {
        "fields": {
          "MerchantName": {"valueString": "스타벅스"},
          "Total": {"valueCurrency": {"amount": 5500}}
        }
      }
    ]
  }
}

실패 시

Result dict:

{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "GUBUN": "Y",
  "RESULT_CODE": "AZURE_ERR",
  "RESULT_MESSAGE": "OCR 실패: <오류 내용>"
}


또한 fail JSON을 파일로 생성한다.

# 1.5 External Dependencies

Azure SDK

azure.ai.formrecognizer.DocumentAnalysisClient

azure.core.credentials.AzureKeyCredential

Python JSON

OS path utilities

# 1.6 Error Handling Strategy
오류 상황	대응 방식
file_path 없음	AssertionError
Azure API 호출 실패	오류 JSON 생성 + RESULT_CODE="AZURE_ERR"
저장 실패	로그 출력 후 반환
기타 예외	전체 파이프라인 중단 없이 오류 정보 반환
# 2. Architecture & Workflow
             [ cropped image (file_path) ]
                           ↓
               run_azure_ocr(record)
                           ↓
        Azure Form Recognizer (prebuilt-receipt)
                           ↓
                 result = poller.result()
                           ↓
         result.to_dict() → JSON 파일 저장
                           ↓
            성공 => dict 반환
            실패 => fail JSON 반환

# 3. Detailed Design (Function-Level Specification)

Doc-processing 단계는 하나의 메인 함수: run_azure_ocr() 로 구성된다.

아래는 처음 보는 개발자도 이해할 수 있도록 상세히 작성한 함수 단위 SDD이다.

## 3.1 run_azure_ocr(duser_input, record)
### Purpose

Crop된 영수증 이미지에 대해 Azure Form Recognizer OCR 서비스를 호출하여
구조화된 OCR JSON을 생성하고 저장한다.

### Inputs
Key	Type	Description
duser_input["azure_endpoint"]	str	Azure Cognitive Service 엔드포인트
duser_input["azure_key"]	str	Azure API Key
duser_input["ocr_json_dir"]	str	OCR 결과 저장 디렉토리
record["file_path"]	str	OCR 수행 대상 이미지 파일 경로
record["FIID"]	str	문서 식별자
record["LINE_INDEX"]	int	문서 라인 식별자
record["RECEIPT_INDEX"]	int	영수증 번호
record["COMMON_YN"]	int	첨부파일 여부
record["GUBUN"]	str	구분 (Y/N 등)
### Outputs
성공 시

Azure OCR 결과(dict)

OCR JSON 파일 저장 (<filename>.ocr.json)

실패 시

오류 결과 JSON 파일 생성

다음과 같은 dict 반환:

{
  "RESULT_CODE": "AZURE_ERR",
  "RESULT_MESSAGE": "OCR 실패: ...",
  "FIID": "...",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0
}

### Workflow (Step-by-Step)
1) 필수 설정값 검증
assert "azure_endpoint" in duser_input
assert "azure_key" in duser_input
assert "ocr_json_dir" in duser_input
assert "file_path" in record


필수 값이 없으면 즉시 오류 발생.

2) DocumentAnalysisClient 생성
client = DocumentAnalysisClient(
    endpoint=endpoint, 
    credential=AzureKeyCredential(key)
)

3) 이미지 파일을 열고 OCR 분석 요청
with open(file_path, "rb") as f:
    poller = client.begin_analyze_document("prebuilt-receipt", document=f)
    result = poller.result()


Azure는 Polling 방식으로 동작하므로 실제 OCR 결과는 poller.result()에서 반환된다.

4) 결과 dict 변환
result_dict = result.to_dict()

5) OCR JSON 파일 저장

파일명 규칙:

<crop_filename>.ocr.json


예: A001_1_1.ocr.json

6) 결과 dict 반환
### Error Handling

OCR 도중 예외 발생 시:

1) fail JSON 생성

이름 규칙:

fail_<FIID>_<LINE_INDEX>_<RECEIPT_INDEX>_<COMMON_YN>.json


내용 예:

{
  "RESULT_CODE": "AZURE_ERR",
  "RESULT_MESSAGE": "OCR 실패: invalid key",
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0
}

2) fail 결과 dict 반환

상위 모듈은 이를 감지하고 Post-processing을 생략하고 DB 저장 루틴만 수행함.

# 4. Data Structures
## 4.1 Input Record Structure
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "GUBUN": "Y",
  "file_path": "/path/to/crop.png"
}

## 4.2 OCR JSON File Example
{
  "modelId": "prebuilt-receipt",
  "apiVersion": "2022-08-31",
  "analyzeResult": {
    "documents": [
      {
        "fields": {
          "MerchantName": {"valueString": "스타벅스"},
          "TransactionDate": {"valueDate": "2025-01-20"},
          "Total": {"valueCurrency": {"amount": 5500}}
        }
      }
    ]
  }
}

## 4.3 OCR Error JSON Structure
{
  "RESULT_CODE": "AZURE_ERR",
  "RESULT_MESSAGE": "OCR 실패: <오류 메시지>",
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "GUBUN": "Y"
}

# 5. Error Cases & Recovery Strategy
Case	Cause	Handling
Azure 인증 오류	잘못된 Key	fail JSON 생성 → RESULT_CODE="AZURE_ERR"
Azure endpoint 오류	잘못된 URL	동일
파일 접근 실패	파일 없음	AssertionError
네트워크 오류	Timeout	실패 JSON 생성
Poller fail	불안정한 Azure 응답	실패 JSON 생성 후 반환

Doc-processing 단계는 중단 없이 다음 레코드로 넘어가는 것이 중요하다.

# 6. Configuration Summary

필요한 환경 변수 및 구성:

Key	Description
azure_endpoint	Azure OCR endpoint
azure_key	Azure Cognitive Services Key
ocr_json_dir	OCR 결과 저장 경로
error_json_dir	오류 JSON 저장 경로
# 7. Additional Notes

출력 JSON은 Post-processing 단계에서 summary/item을 생성하는 중요 입력값이다.

OCR이 실패해도 파이프라인은 중단되지 않도록 설계되어 있음.

Azure 호출은 비용이 발생하므로 재호출 방지를 위해 캐싱 전략도 선택 가능(추후 확장 영역).