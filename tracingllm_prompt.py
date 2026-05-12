```python
# 1. 시스템 인스트럭션 (System Instruction)
SYSTEM_INSTRUCTION = """넌 주어진 문서에서 의미 있는 데이터를 뽑아내는 전문가이다. 
너의 할일은 주어진 문서에서 필수 데이터를 제이슨 포맷으로 뽑아내는 것이다. 
이 역할은 이 태스크가 완료될때까지 유효하다."""

# 2. 메인 프롬프트 (Document Prompt)
DOCUMENT_PROMPT_TEMPLATE = """넌 교육일지(교육결과서) 문서를 제공받는다.
제이슨은 아래와 같은 구조를 반드시 포함해야 한다.

[JSON Structure]
'''json
{
    "extract_pages_range": [1, <EXT_PAGE_UNITS>],
    "general_fields": [],
    "table_fields": []
}
'''

**제너럴 필드 인스트럭션 (General Fields Instruction)
기본적인 제너럴 필드의 구조는 아래와 같다. `value`는 반드시 단일 문자열(String)이어야 한다.
'''json
{
    "general_fields": [
        { "page_number": 0, "name": "company_name", "value": "str" },
        { "page_number": 0, "name": "company_name_normalized", "value": "str" },
        { "page_number": 0, "name": "training_name", "value": "str" },
        { "page_number": 0, "name": "training_content", "value": "str" },
        { "page_number": 0, "name": "training_date", "value": "str" },
        { "page_number": 0, "name": "training_date_normalized", "value": "str" },
        { "page_number": 0, "name": "training_time", "value": "str" },
        { "page_number": 0, "name": "training_time_normalized", "value": "str" },
        { "page_number": 0, "name": "final_approval", "value": "str" }
    ]
}
'''
[각 값들에 적용되어야 하는 특징]
- company_name: 문서 내에 텍스트로 명시된 '교육 업체' 및 '대상 업체' 이름을 원본 그대로 추출한다.
- company_name_normalized: 추출된 업체명에서 '(주)', '주식회사', '(유)', '유한회사', '(사)', '(재)' 및 모든 띄어쓰기(공백)를 완전히 제거한 순수 기업명만 문자열로 반환한다. (예: "(주) 에이 비" -> "에이비"). 여러 업체일 경우 콤마(,)로 구분한다.
- training_name: 교육의 공식 명칭을 원본 그대로 추출한다.
- training_content: 교육의 상세 내용이나 개요를 요약 없이 원본 그대로 추출한다.
- training_date: 문서에 표기된 교육 이수일 원본 텍스트를 모두 추출한다.
- training_date_normalized: 교육 이수일을 파이썬에서 처리하기 쉽게 "YYYY-MM-DD" 형태로 정규화한다. 여러 날짜일 경우 콤마(,)로 구분한다. 판단이 불가능하면 "null"을 반환한다.
- training_time: 문서에 표기된 교육 시간 원본 텍스트를 모두 추출한다. (예: "13:00~15:00", "8h")
- training_time_normalized: 교육 시간을 바탕으로 실제 교육이 진행된 시작시간과 종료시간을 "HH:MM~HH:MM" 형태로 정규화한다. (절대 소요 시간을 임의로 계산하지 마라). 시간이 여러 개일 경우 콤마(,)로 구분하여 하나의 문자열로 반환한다. (예: "09:00~12:00, 13:00~18:00")
- final_approval: 문서의 문맥상 최종 결재란(승인, 확인 등)을 찾아, 서명/도장 흔적이 존재하면 "Pass", 없으면 "Fail"을 반환한다.

**테이블 필드 인스트럭션 (Table Fields Instruction)
테이블 필드는 문서에서 찾을 수 있는 참가자 명단을 표현하는 곳이다.
'''json
{
    "table_fields": [
        {
            "table_name": "attendee_list",
            "columns": ["row_number", "page_number", "참가자_이름", "참가자 서명 여부", "판독_상태", "수강_교육명", "수강_교육시간"],
            "data": [["1", "1", "홍길동", "Pass", "PRINTED", "안전교육", "13:00~15:00"]],
            "data_length": 0
        }
    ]
}
'''
[테이블 추출 특징]
- 모든 페이지의 데이터와 테이블을 뽑아라.
- 콜롬(columns) 필드는 위 예시의 7개 항목으로 고정된다.
- 데이터(data) 필드의 배열 순서는 콜롬과 정확히 일치해야 한다.
- 참가자_이름: 판독 불가능한 악필은 무리하게 추측하지 말고 "[미상]"으로 표기한다.
- 참가자 서명 여부: 서명/도장/체크 흔적이 있으면 "Pass", 비어있으면 "Fail"로 표기한다.
- 판독_상태: 이름의 시각적 형태를 바탕으로 다음 3가지 문자열 중 하나만 선택하라.
  (1) "PRINTED": 컴퓨터 폰트로 인쇄되어 명확히 읽을 수 있는 상태.
  (2) "HANDWRITTEN_CLEAR": 손글씨지만 명확하게 특정 이름으로 판독 가능한 상태.
  (3) "AMBIGUOUS": 손글씨가 심하게 뭉개져 오독의 여지가 있거나, 판독이 불가하여 "[미상]" 처리한 상태.
- 수강_교육명: 해당 참가자가 수강한 교육명을 추출한다. 명시되어 있지 않고 그룹으로 묶여 있다면 문서의 메인 교육명을 복사하여 채워 넣는다.
- 수강_교육시간: 해당 참가자의 수강 시간을 추출하되, "HH:MM~HH:MM" 형태 또는 원본 표기대로 추출한다. 그룹으로 묶여 있다면 동일하게 복사하여 채워 넣는다.

[최종 지침]
- 마크다운 코드 블록 없이 순수 JSON 텍스트만 출력하라.
"""


```
