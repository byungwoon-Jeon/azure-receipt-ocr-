📄 Extractor Module – Software Design Document (SDD)

Version 1.0 — Markdown Edition

# 1. Module Overview
## 1.1 Purpose

Extractor 모듈은 OCR 자동화 전체 파이프라인의 시작점(Entry Point) 이다.
이 모듈의 역할은 다음과 같다:

SAP HANA DB에서 OCR 대상 레코드를 조회

각 레코드를 스레드 기반 병렬 처리

전처리 → OCR → 후처리 → DB 저장의 전체 프로세스를 오케스트레이션

단계별 오류를 캐치하고 fail JSON + DB Insert 수행

즉, Extractor는 전체 파이프라인을 관리·조율하는 상위 컨트롤러 역할을 수행한다.

## 1.2 Responsibilities

DB 조회: target_date 기준으로 OCR 대상 레코드 조회

병렬 처리: run_in_multi_thread 이용

전체 파이프라인 제어

Pre-Processing

Document Processing (Azure OCR)

Post-Processing

DB Insert

오류 처리 흐름 제어

작업 디렉토리 구조 초기화

## 1.3 Inputs
Name	Type	Description
duser_input	dict	DB, 디렉토리, Azure Key, YOLO 모델 경로 등 전체 설정값
## 1.4 Outputs

Extractor는 값을 반환하지 않는다.
대신 내부에서 다음 출력물을 생성한다:

Preprocess Crop 이미지

Azure OCR JSON

Postprocess 결과 JSON

Fail JSON

DB Insert 결과

즉, 부수효과(side-effect)를 통해 파이프라인 작업을 완결한다.

## 1.5 External Dependencies

SAP HANA DB (SQLAlchemy)

YOLO 모델

Azure Form Recognizer OCR

파일 시스템 경로

idp_utils.run_in_multi_thread

## 1.6 Error Handling Strategy

각 단계 실패 시 fail JSON 생성 및 DB Insert

오류는 상위로 전파되지 않음(레코드 단위로 캡슐화)

전체 파이프라인은 중단되지 않음

# 2. Architecture & Workflow
[DB Query]
    ↓
Data Records (N rows)
    ↓
[Multi-thread Execution]
    ↓
For each record → execute_worker():
      1) Pre-process
      2) Azure OCR
      3) Post-process
      4) DB Insert


Extractor는 단순히 “한 건씩 처리”가 아니라
“여러 건을 동시에 처리하는 병렬 오케스트레이터”이다.

# 3. Detailed Design (Function-Level Specification)

아래는 Extractor의 모든 주요 함수에 대한 상세 설명이다.
처음 보는 개발자도 이해할 수 있도록 입력/출력/동작 흐름/에러 처리까지 모두 포함된다.

## 3.1 execute(duser_input)
### Purpose

OCR 파이프라인 전체를 시작하는 최상위 Entry Function.

### Inputs
Name	Type	Description
duser_input	dict	전체 환경 설정
### Outputs

반환값 없음

파일 생성 / JSON 생성 / DB 기록을 내부적으로 수행

### Workflow

작업 경로 구성

duser_input = das_process_setup(duser_input)


DB 조회 실행

data_records = query_data_by_date(duser_input)


데이터가 없으면 종료

각 레코드를 처리할 파라미터 목록 생성

병렬 처리 실행

idp_utils.run_in_multi_thread(adapter_execute_worker, func_params_list)


종료 로그 출력

### Error Handling

실행 중 오류는 로그만 출력하고 전체 중단 없음

## 3.2 das_process_setup(duser_input)
### Purpose

파이프라인 실행을 위한 디렉토리 구조 생성 및 환경 초기화.

### Workflow

다음과 같은 구조의 디렉토리가 자동 생성된다:

Workspace/YYYYMMDD/
  ├── PreProcess/
  │     ├── RawFile/
  │     ├── MergeDoc/
  │     └── Cropped/
  ├── DocProcess/
  │     ├── Azure/
  │     └── Error/
  └── PostProcess/

### Outputs

경로가 포함된 duser_input dict 반환

### Error Handling

디렉토리 생성 실패 시 로그 출력

프로세스는 계속 진행

## 3.3 execute_worker(record, duser_input)
### Purpose

레코드 1건에 대해 전체 OCR 파이프라인을 수행한다.

즉:

전처리 → OCR → 후처리 → DB 저장

### Inputs
Name	Type	Description
record	dict	DB 조회 레코드
duser_input	dict	전체 설정
### Workflow
1) Pre-processing 실행
cropped_list = run_pre_pre_process(duser_input, record)

전처리 실패 처리

fail JSON 생성

DB 저장

해당 레코드는 즉시 종료

2) OCR 실행 (Azure)

각 crop 이미지마다:

ocr_result = run_azure_ocr(duser_input, cropped)


OCR 실패 시:

AZURE_ERR JSON 생성

DB 저장 후 다음 crop 처리

3) Post-processing 실행

성공한 OCR에 한하여:

post_path = post_process_and_save(...)

4) DB Insert
insert_postprocessed_result(post_path)

### Error Handling

각 단계 오류는 fail JSON 생성 후 다음 단계로 진행하지 않음

치명적 오류는 logger.error 로 기록

## 3.4 write_fail_and_insert(...)
### Purpose

전처리/YOLO/OCR 단계 실패 시 fail JSON을 생성하고 DB 저장을 수행한다.

### Inputs
Name	Description
duser_input	환경 설정
base	FIID, LINE_INDEX 등 기본 정보
code	오류 코드
message	오류 메시지
attach_file	원본 파일 URL
receipt_index	실패한 영수증 번호
### Workflow

summary JSON 구성

fail JSON 파일 생성

DB Insert 실행

### Error Handling

JSON 생성 실패 → 로그만 출력

DB insert 실패 → 로그만 출력

## 3.5 adapter_execute_worker(params)
### Purpose

멀티스레드 실행을 위해 execute_worker() 를 감싸는 wrapper.

### Workflow
return execute_worker(record, duser_input)

# 4. Data Structures
## 4.1 Input Record Example
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "GUBUN": "Y",
  "ATTACH_FILE": "http://example.com/img.jpg",
  "FILE_PATH": null
}

## 4.2 Pre-processing Output Example
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "file_path": "/PreProcess/Cropped/A001_1.png"
}

## 4.3 OCR Error Output
{
  "RESULT_CODE": "AZURE_ERR",
  "RESULT_MESSAGE": "OCR 호출 실패",
  "FIID": "A001",
  "LINE_INDEX": 1
}

## 4.4 Fail JSON Structure
{
  "summary": {
    "FIID": "A001",
    "LINE_INDEX": 1,
    "RECEIPT_INDEX": 1,
    "RESULT_CODE": "500",
    "RESULT_MESSAGE": "전처리 실패"
  },
  "items": []
}

# 5. Error Handling Table
단계	오류	처리 방식
파일 다운로드	URL 접속 실패	fail JSON 생성 후 DB 저장
YOLO	탐지 없음(E001)	오류 JSON 생성
OCR	Azure 호출 실패	AZURE_ERR JSON 생성
후처리	필드 누락	POST_ERR 생성
DB 저장	Insert 실패	로그만 기록
# 6. Configuration Summary

Workspace 디렉토리

PreProcess/DocProcess/PostProcess 구조

SQLAlchemy 연결 정보

Azure OCR endpoint/key

YOLO 모델 경로