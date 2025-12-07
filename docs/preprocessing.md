📄 Pre-processing Module – Software Design Document (SDD)

Version 1.0 — Markdown Edition

# 1. Module Overview
## 1.1 Purpose

Pre-processing 모듈은 OCR을 수행하기 전에 원본 문서를 가공하여 정제된 OCR 입력 이미지를 생성하는 핵심 단계이다.

이 모듈은 다음 기능을 수행한다:

파일 다운로드 (HTTP / 내부 서버 파일 / EGSS SSO 기반 다운로드)

DRM 문서 해제

문서(PDF, DOCX, PPTX, XLSX) 내부 이미지 추출

이미지 병합(merged.png) 생성

PNG 변환

YOLO 모델을 이용한 영수증 Crop 처리

Crop 결과를 structured dict 형태로 상위 모듈에 반환

즉, Pre-processing은 OCR이 읽기 좋은 최적의 이미지 생성을 목표로 한다.

# 1.2 Responsibilities

URL 기반 파일 다운로드 및 저장

DRM 해제 API 통신

문서 파일(PDF/DOCX/PPTX/XLSX)에서 이미지 추출

이미지 병합 및 PNG 변환 수행

YOLO 모델을 사용한 객체 탐지 및 Crop

성공/실패 여부에 따른 RESULT_CODE/RESULT_MESSAGE 생성

Crop된 이미지 정보 리스트 반환

# 1.3 Inputs
Key	Type	Description
in_params / duser_input	dict	다운로드 경로, 모델 경로, merged_dir 등 설정값
db_record	dict	FIID, LINE_INDEX, GUBUN, ATTACH_FILE, FILE_PATH 등 OCR 대상 정보
# 1.4 Outputs

list[dict] 형태의 결과 목록을 반환한다.

성공 예:

[
  {
    "FIID": "A001",
    "LINE_INDEX": 1,
    "RECEIPT_INDEX": 1,
    "COMMON_YN": 0,
    "GUBUN": "Y",
    "file_path": "/Cropped/A001_1_1.png"
  }
]


오류 발생 시:

[
  {
    "FIID": "A001",
    "LINE_INDEX": 1,
    "RESULT_CODE": "E001",
    "RESULT_MESSAGE": "YOLO 탐지 실패"
  }
]

# 1.5 External Dependencies

Python requests

Playwright (SSO 자동 로그인 다운로드)

Pillow (PIL)

PyMuPDF (PDF 처리)

zipfile (DOCX/PPTX/XLSX 이미지 추출)

YOLO (ultralytics)

OS, Pathlib

# 1.6 Error Handling Strategy

파일 다운로드 실패 → None 반환 → 상위 모듈에서 Fail JSON 처리

이미지 추출 실패 → WARNING 로그 후 None 처리

YOLO 탐지 실패 → RESULT_CODE: E001

PNG 변환 실패 → Exception → 상위 모듈로 empty list 반환

DRM 해제 실패 → 원본 파일 그대로 사용

# 2. Architecture & Workflow
                [ db_record ]
                      ↓
           download_file_from_url()
                      ↓
          ┌─────────────────────────┐
          │  문서 파일인지 판별?     │
          └───────────┬─────────────┘
                      │Yes
                      ▼
         process_document_file()
     (DRM 해제 → 이미지 추출 → 병합)
                      ↓
               convert_to_png()
                      ↓
    YOLO Model 탐지 → crop_receipts_with_yolo()
                      ↓
            [ cropped_list 반환 ]

# 3. Detailed Design (Function-Level Specification)

아래는 대상 모듈의 모든 함수에 대해 상세히 설명한 SDD다.
인수인계 문서 수준으로 충분히 자세히 작성했다.

## 3.1 download_r_link_with_sso(url, sso_id, sso_pw, download_dir, headless=False)
### Purpose

EGSS 시스템의 R로 시작하는 내부 링크를 SSO 인증 후 자동 다운로드한다.

### Inputs

url: R 링크

sso_id, sso_pw: Playwright 자동 로그인에 사용

download_dir: 다운로드 저장 경로

### Workflow

Playwright 브라우저 실행

EGSS 로그인 페이지 이동

ID/PW 자동 입력

다운로드 감지 후 저장

저장된 파일 경로 반환

### Outputs

다운로드 성공 → file path

실패 → None

## 3.2 call_drm_decode_api(file_path)
### Purpose

DRM 해제 API 호출 후 DRM-free 문서를 생성한다.

### Workflow

POST API 요청

성공 → response["data"]에 새 파일 경로 반환

실패 → 원본 파일을 그대로 사용

### Outputs

DRM 해제된 파일 경로 or 기존 파일 경로

## 3.3 extract_images_from_document(file_path)
### Purpose

문서(PDF/DOCX/PPTX/XLSX)에서 이미지 리스트(PIL Image)를 추출한다.

### Workflow
Case 1) PDF

PyMuPDF로 페이지별 렌더링 후 이미지 추출

Case 2) DOCX/PPTX/XLSX

zipfile open → /media/ 폴더 내부 이미지 파일만 파싱

### Outputs

이미지 리스트 (빈 리스트 가능)

## 3.4 merge_images_vertically(images, output_path)
### Purpose

이미지 여러 장을 세로로 이어붙여 하나의 긴 merged 이미지로 만든다.

### Workflow

최대 너비 계산

전체 높이 합산

새 이미지(canvas) 생성

각 이미지를 y-offset 쌓아붙임

### Output Path

<filename>_merged.png

## 3.5 process_document_file(file_path, merged_doc_dir)
### Purpose

문서 파일 처리 전체 단계 담당:

DRM 해제 → 이미지 추출 → 병합 → merged.png 생성

### Workflow

파일 확장자 확인

DRM decode 실행

이미지 추출

이미지 병합

DRM 해제 파일 삭제

### Outputs

merged PNG 파일 경로

이미지 없으면 None

## 3.6 validate_file_size(path)
Purpose

이미지 크기가 10MB 이상이면 OCR에 부적합하므로 오류 발생.

## 3.7 download_file_from_url(url, save_dir, is_file_path=False)
### Purpose

모든 형태의 URL을 처리하는 "통합 다운로드 함수".

### 지원 종류

R 링크 (SSO)

HTTP/HTTPS 링크

내부 파일 경로 (is_file_path=True)

### Workflow

R 링크일 경우 → download_r_link_with_sso() 호출

파일 경로일 경우 root domain 자동 prefix

requests.get() 다운로드

파일 크기 검사

저장 후 경로 반환

### Outputs

파일 경로

실패 → None

## 3.8 convert_to_png(input_path, save_dir)
### Purpose

OCR 입력을 위해 모든 이미지를 PNG로 통일한다.

### Workflow

이미지 로드

RGB 변환

save_dir에 PNG로 저장

## 3.9 crop_receipts_with_yolo(model, png_path, ...)
### Purpose

YOLO 모델로 영수증 영역(Receipt)을 탐지하고 Crop한다.

### Workflow

YOLO inference

bounding box 좌표 획득

ATTACH_FILE은 1개의 bbox만 인정

FILE_PATH는 여러 개 가능

Crop 후 파일 저장

### Outputs 예시

성공:

{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "file_path": "Cropped/A001_1.png"
}


오류:

{
  "RESULT_CODE": "E002",
  "RESULT_MESSAGE": "ATTACH_FILE에서 2개 이상 YOLO 탐지됨"
}

## 3.10 run_pre_pre_process(in_params, db_record)
### Purpose

Pre-processing 전체 단계를 실행하고 Crop 결과 리스트를 반환하는 “핵심 함수”.

### Workflow

파일 다운로드

문서인 경우 → process_document_file()

PNG 변환

YOLO Crop 실행

모든 Crop 정보를 리스트로 반환

### Outputs

성공 시 list[dict]

오류 발생 시 empty list

# 4. Data Structures
## 4.1 db_record 구조
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "GUBUN": "Y",
  "ATTACH_FILE": "http://image.jpg",
  "FILE_PATH": null
}

## 4.2 Crop 결과 구조
{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "GUBUN": "Y",
  "RECEIPT_INDEX": 1,
  "COMMON_YN": 0,
  "file_path": "/Cropped/A001_1.png"
}

# 5. Error Cases & Handling
단계	오류	반환 / 처리 방식
파일 다운로드	404 / timeout	None 반환 (상위에서 fail JSON 처리)
DRM 해제	API 실패	원본 파일 사용
문서 이미지 추출	이미지 없음	None → 상위에서 fail 처리
PNG 변환	손상된 파일	Exception 발생
YOLO	탐지 없음	RESULT_CODE="E001"
YOLO	ATTACH_FILE에서 2개 이상	RESULT_CODE="E002"
# 6. Configuration Summary

download_dir

merged_doc_dir

cropped_dir

yolo_model_path

파일 크기 제한 10MB

SSO 환경 변수

EGSS_SSO_ID

EGSS_SSO_PW