📄 Post-processing Module – Software Design Document (SDD)

Version 1.0 — Markdown Edition

# 1. Module Overview
## 1.1 Purpose

Post-processing 모듈은 Azure OCR 결과(JSON) 를 입력받아 다음 작업을 수행한다:

OCR 결과를 기반으로 요약(summary) 정보 생성

품목(item) 리스트 구조화

결과 JSON 파일 저장

오류 발생 시 오류 JSON 생성

DB Insert 단계에서 사용할 정규화된 데이터 제공

즉, Post-processing은 **“Azure OCR 원본 데이터를 → 비즈니스 로직에 맞는 정제된 구조화 데이터로 가공하는 단계”**이다.

## 1.2 Responsibilities

OCR JSON 파일 읽기

OCR 필드 파싱 (총액, 상호명, 날짜, 품목 리스트 등)

Summary(dict) 생성

Items(list[dict]) 생성

후처리 JSON 저장

후처리 오류 처리 및 fail JSON 저장

## 1.3 Inputs
Key	Type	Description
duser_input["postprocess_output_dir"]	str	후처리 JSON 저장 경로
record["json_path"]	str	OCR JSON 파일 경로
record["FIID"]	str	문서 식별자
record["LINE_INDEX"]	int	라인 번호
record["RECEIPT_INDEX"]	int	영수증 인덱스
record["COMMON_YN"]	int	공통 여부
record["GUBUN"]	str	구분(Y/N 등)
record["ATTACH_FILE"]	str	원본 파일 URL
## 1.4 Outputs
✔ 성공 시

정규화된 후처리 JSON 파일 생성
출력 파일 예:

<FIID>_<LINE_INDEX>_<RECEIPT_INDEX>_post.json


내부 구조:

{
  "summary": { ... },
  "items": [ ... ]
}

✔ 실패 시

실패용 JSON 파일 생성:

fail_<FIID>_<LINE_INDEX>_post.json


내용:

{
  "summary": {
    "RESULT_CODE": "POST_ERR",
    "RESULT_MESSAGE": "<오류 내용>"
  },
  "items": []
}

## 1.5 External Dependencies

JSON 파일 로딩 및 저장

OS path utilities

datetime (CREATE_DATE, UPDATE_DATE)

Python logging

## 1.6 Error Handling Strategy
오류 상황	처리 방식
OCR JSON 파일 없음	FileNotFoundError → fail JSON 생성
OCR JSON 구조 오류	Exception → fail JSON 생성
필드 누락	summary 값 None으로 대체
품목 파싱 실패	items 빈 리스트 반환
전체 실패	POST_ERR 코드로 fail JSON 기록
# 2. Architecture & Workflow
[ OCR JSON 파일 ]
        ↓
load JSON
        ↓
fields 파싱
        ↓
summary 생성
        ↓
item_list 생성
        ↓
후처리 결과 JSON 저장
        ↓
return output_path


오류 발생 시:

예외 발생 → fail JSON 생성 → fail_path 반환

# 3. Detailed Design (Function-Level Specification)

Post-processing 모듈은 핵심 함수 post_process_and_save() 로 이루어져 있다.
아래는 이 함수를 처음 보는 사람도 이해할 수 있을 정도로 상세하게 설명한다.

## 3.1 post_process_and_save(duser_input, record)
### Purpose

OCR 결과(JSON)를 정규화된 summary + items 구조로 변환

후처리 결과 JSON 파일을 저장

오류 발생 시 error JSON을 생성

### Inputs
Key	Type	Description
duser_input["postprocess_output_dir"]	str	저장 디렉토리
duser_input["error_json_dir"]	str	실패 JSON 저장 디렉토리
record["json_path"]	str	OCR JSON 경로
record["FIID"]	str	FIID
record["LINE_INDEX"]	int	기본 인덱스
record["RECEIPT_INDEX"]	int	영수증 번호
record["COMMON_YN"]	int	공통 여부
record["ATTACH_FILE"]	str	원본 파일 URL
record["GUBUN"]	str	구분
### Outputs
성공 시:

후처리 JSON 파일 경로 반환

실패 시:

fail JSON 파일 생성 후 그 경로 반환

### Workflow (Step-by-Step)
1) 필수 입력값 검증
assert "postprocess_output_dir" in duser_input
assert "json_path" in record

2) OCR JSON 파일을 읽는다
with open(json_path, "r") as f:
    data = json.load(f)


OCR 결과 기본 구조:

{
  "analyzeResult": {
    "documents": [
      { "fields": { ... } }
    ]
  }
}

3) fields 추출
doc = data.get("analyzeResult", {}).get("documents", [{}])[0]
fields = doc.get("fields", {})

4) Summary 생성

summary는 아래 항목을 생성한다:

key	설명
COUNTRY	국가
RECEIPT_TYPE	영수증 유형
MERCHANT_NAME	상호명
MERCHANT_PHONE_NO	전화번호
TRANSACTION_DATE	날짜
TRANSACTION_TIME	시간
TOTAL_AMOUNT	총액
TAX_AMOUNT	세금
SUMTOTAL_AMOUNT	공급가액
RESULT_CODE	기본 200
RESULT_MESSAGE	SUCCESS

예:

{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "MERCHANT_NAME": "스타벅스",
  "TOTAL_AMOUNT": "5500",
  "RESULT_CODE": 200,
  "RESULT_MESSAGE": "SUCCESS"
}

5) Item 리스트 생성

OCR 모델의 item 구조:

"Items": {
  "valueArray": [
    {
      "valueObject": {
        "Description": {"valueString": "..."},
        "Quantity": {"valueNumber": ...},
        "Price": {"valueCurrency": {"amount": ...}},
        "TotalPrice": {"valueCurrency": {"amount": ...}}
      }
    }
  ]
}


파싱 후:

{
  "ITEM_INDEX": 1,
  "ITEM_NAME": "아메리카노",
  "ITEM_QTY": "1",
  "ITEM_UNIT_PRICE": "4500",
  "ITEM_TOTAL_PRICE": "4500"
}

6) 결과 JSON 저장

파일명 규칙:

<FIID>_<LINE_INDEX>_<RECEIPT_INDEX>_post.json

json.dump(result_json, f, indent=2)

7) 성공 시 output_path 반환
### Error Handling
발생 가능한 오류:

OCR JSON 없음

OCR JSON 구조 변경

필드 파싱 오류

파일 저장 실패

처리 방식:

오류 로그 출력

아래 구조의 fail JSON 생성

{
  "summary": {
    "FIID": "A001",
    "LINE_INDEX": 1,
    "RECEIPT_INDEX": 1,
    "RESULT_CODE": "POST_ERR",
    "RESULT_MESSAGE": "오류 상세 메시지"
  },
  "items": []
}


fail JSON 파일 경로 반환

# 4. Data Structures
## 4.1 후처리 Summary 구조
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "GUBUN": "Y",
  "ATTACH_FILE": "http://file.png",
  "COUNTRY": "KR",
  "RECEIPT_TYPE": "Café",
  "MERCHANT_NAME": "스타벅스",
  "TRANSACTION_DATE": "2025-01-20",
  "TOTAL_AMOUNT": "5500",
  "RESULT_CODE": 200,
  "RESULT_MESSAGE": "SUCCESS"
}

## 4.2 아이템 구조
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "ITEM_INDEX": 1,
  "ITEM_NAME": "아메리카노",
  "ITEM_QTY": "1",
  "ITEM_UNIT_PRICE": "4500",
  "ITEM_TOTAL_PRICE": "4500"
}

## 4.3 실패 JSON 구조
{
  "summary": {
    "FIID": "A001",
    "LINE_INDEX": 1,
    "RESULT_CODE": "POST_ERR",
    "RESULT_MESSAGE": "OCR 파일 없음"
  },
  "items": []
}

# 5. Error Cases & Handling Strategy
Case	Handling
OCR JSON 파일 없음	fail JSON 생성
OCR JSON 구조 파싱 실패	RESULT_CODE="POST_ERR"
Items가 없음	items 빈 리스트로 처리
Summary 필드 누락	None으로 채움
파일 저장 실패	fail JSON 생성
# 6. Configuration Summary
Key	Description
postprocess_output_dir	후처리 JSON 저장 경로
error_json_dir	실패 저장 경로
JSON indent = 2	사람이 읽기 좋게 저장
# 7. Role in the Entire Pipeline

Pre-processing → Doc-processing → Post-processing → DB Master
에서 Post-processing은 DB 저장 가능한 형태로 데이터를 조립하는 마지막 가공 단계이다.