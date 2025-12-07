📄 DB Master Module – Software Design Document (SDD)

Version 1.0 — Markdown Edition

# 1. Module Overview
## 1.1 Purpose

DB Master 모듈은 OCR Pipeline의 마지막 단계로서,
후처리(Post-processing) 결과 JSON을 SAP HANA DB에 저장하는 역할을 수행한다.

이 모듈의 핵심 목적은 다음과 같다:

Post-processing JSON 파일 로드

Summary / Items 데이터 분리 및 매핑

SAP HANA 대상 테이블 INSERT 수행

FAIL/ERROR 케이스 DB 반영

DB Connection 및 Commit/Rollback 제어

즉, OCR → 후처리까지 생성한 데이터를 최종적으로 DB에 반영하는 핵심 저장 모듈이다.

# 1.2 Responsibilities

JSON 결과 파일 로딩

DataFrame 변환 또는 dict 매핑

Summary 데이터 INSERT

Item 데이터 INSERT (여러 행)

올바른 PK(FIID, LINE_INDEX, RECEIPT_INDEX, ITEM_INDEX 등) 관리

실패(Fail JSON)도 DB에 저장

DB 연결 객체 관리 및 예외 처리

# 1.3 Inputs
Key	Type	Description
json_path	str	후처리 JSON 파일 경로
sqlalchemy_conn	object	SQLAlchemy connection (HANA)
table_summary	str	Summary 저장 테이블명
table_items	str	Item 저장 테이블명
# 1.4 Outputs
성공 시

Summary 1건 insert

Items N건 insert

로그 출력 후 정상 종료

실패 시

오류 메시지를 포함한 로그 출력

rollback 수행

실패한 레코드도 Summary 테이블에 저장(FAIL 기록)

즉, DB Master는 OCR 파이프라인의 최종 결과를 책임지고 DB에 반영하는 단계다.

# 1.5 External Dependencies

SQLAlchemy (sap_hana dialect)

JSON 파일 로딩

datetime for CREATE_TIME

Python logging

# 1.6 Error Handling Strategy
상황	처리 방식
JSON 로드 실패	INSERT 스킵 + 로그 출력
Summary INSERT 실패	rollback → 오류 로그
Items INSERT 실패	rollback → Summary 실패 기록만 저장
DB connection 오류	프로세스 종료 또는 상위 모듈로 오류 반환
PK 중복	ON CONFLICT 또는 replace 전략 수행(설정에 따라)
# 2. Architecture & Workflow
        [ postprocessing JSON ]
                    ↓
          load JSON from file
                    ↓
    extract summary fields & items
                    ↓
  INSERT INTO RPA_CCR_LINE_SUMM (summary)
                    ↓
  INSERT INTO RPA_CCR_LINE_ITEMS (items)
        (N rows per receipt)
                    ↓
              COMMIT & DONE


오류 발생 시:

Exception → ROLLBACK → FAIL summary INSERT → DONE

# 3. Detailed Design (Function-Level Specification)

여기서는 실제 DB Master 모듈에서 사용되는 대표 함수들을
처음 보는 사람도 이해하기 쉬운 SDD 형태로 상세히 기술한다.

## 3.1 insert_postprocessed_result(json_path, conn, table_summary, table_items)
### Purpose

후처리 JSON 파일을 로드하여:

Summary (1 row)

Items (0~N rows)

를 DB에 INSERT 하는 핵심 함수.

OCR Pipeline의 “최종 저장 단계”이다.

### Inputs
Key	Type	Description
json_path	str	후처리 JSON 파일 경로
conn	SQLAlchemy Connection	HANA DB 커넥션
table_summary	str	요약 저장 테이블명
table_items	str	품목 저장 테이블명
### Outputs

성공 시: None (정상 로그 출력)

실패 시: 예외 발생 → rollback → fail summary insert

### Workflow (Step-by-Step)
1) JSON 파일 로드
with open(json_path, "r") as f:
    data = json.load(f)


JSON 구조:

{
  "summary": { ... },
  "items": [ ... ]
}

2) Summary 추출

예:

{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RECEIPT_INDEX": 1,
  "TOTAL_AMOUNT": 5500,
  "RESULT_CODE": 200,
  "RESULT_MESSAGE": "SUCCESS"
}


DB 매핑 시 필요한 default 값 추가:

CREATE_TIME

UPDATE_TIME

CREATE_USER

3) Items 추출

예:

[
  {
    "ITEM_INDEX": 1,
    "ITEM_NAME": "아메리카노",
    "ITEM_QTY": 1,
    "ITEM_TOTAL_PRICE": 4500
  }
]


없을 경우 빈 리스트로 처리.

4) Summary INSERT
INSERT INTO RPA_CCR_LINE_SUMM (...)
VALUES (...)


1개 row mandatory

RESULT_CODE가 FAIL이어도 기록은 반드시 남겨야 함

5) Items INSERT (반복)
INSERT INTO RPA_CCR_LINE_ITEMS (...)
VALUES (...)


0개 이상 반복

ITEM_INDEX 기준

6) Commit

모든 INSERT 성공 시:

conn.commit()

7) 실패 시 처리 흐름

예외 발생 → rollback → fail summary insert 시도

fail summary 예:

{
  "FIID": "A001",
  "LINE_INDEX": 1,
  "RESULT_CODE": "DB_ERR",
  "RESULT_MESSAGE": "Insert 실패"
}

### Error Handling Logic
Case 1) Summary INSERT 실패

➡ rollback 수행
➡ fail summary insert 실행
➡ 종료

Case 2) Item INSERT 중 실패

➡ rollback 수행
➡ fail summary insert 실행
➡ 종료

Case 3) JSON 파일 자체 없음

➡ 바로 fail summary insert

# 4. Data Structures
## 4.1 Summary Table Schema (예시)
Column	Type	Description
FIID	VARCHAR	문서 ID
LINE_INDEX	INT	라인 번호
RECEIPT_INDEX	INT	영수증 번호
MERCHANT_NAME	VARCHAR	상호명
TRANSACTION_DATE	DATE	거래일
TOTAL_AMOUNT	NUMBER	총액
RESULT_CODE	VARCHAR	처리 코드
RESULT_MESSAGE	VARCHAR	메시지
CREATE_TIME	TIMESTAMP	생성 시각
## 4.2 Item Table Schema (예시)
Column	Type	Description
FIID	VARCHAR	문서 ID
LINE_INDEX	INT	라인 번호
RECEIPT_INDEX	INT	영수증 번호
ITEM_INDEX	INT	항목 번호
ITEM_NAME	VARCHAR	품목명
ITEM_QTY	NUMBER	수량
ITEM_UNIT_PRICE	NUMBER	단가
ITEM_TOTAL_PRICE	NUMBER	총액
CREATE_TIME	TIMESTAMP	생성 시간
# 5. Error Cases & Handling
오류 상황	처리 방식
JSON 파일 없음	FAIL summary insert
JSON 구조 오류	FAIL summary insert
Summary insert 실패	rollback → FAIL summary insert
Item insert 실패	rollback → FAIL summary insert
DB connection 끊김	예외 발생 후 종료
PK 충돌	로그 출력 후 skip 또는 replace 전략(구성 옵션)
# 6. Configuration Summary
Key	Description
table_summary	Summary 저장 테이블
table_items	Item 저장 테이블
sqlalchemy_conn	HANA DB Connection
json_path	후처리 JSON 경로
# 7. Role in Entire OCR Pipeline

전체 OCR 파이프라인에서 DB Master의 위치:

Pre-processing → Doc-processing → Post-processing → **DB Master**


DB Master는 가장 마지막 단계이므로,
OCR 파이프라인의 결과를 기업 시스템에 반영하는 최종 확정 단계다.

이 단계가 성공해야 비로소 “해당 문서 처리 완료”로 간주된다.

# 8. Additional Notes for Maintenance

CREATE_TIME / UPDATE_TIME는 실제 운영 정책에 따라 자동 생성 가능

DB 연결 오류 시 retry 전략 도입 가능

PK 중복 방지를 위해 처리 전 DELETE 전략도 선택 가능

대량 insert가 필요할 경우 batch insert 최적화 가능