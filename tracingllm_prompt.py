```python
# 1. System Instruction
SYSTEM_INSTRUCTION = """You are an expert in extracting meaningful data from given documents. 
Your task is to extract essential data from the document into a strict JSON format. 
This role remains active until the task is completed."""

# 2. Main Document Prompt
DOCUMENT_PROMPT_TEMPLATE = """You are provided with a training log (training result report) document.
Your JSON output MUST strictly include the structure below.

[JSON Structure]
'''json
{
    "extract_pages_range": [1, <EXT_PAGE_UNITS>],
    "general_fields": [],
    "table_fields": []
}
'''

**General Fields Instruction
The basic structure of general fields is as follows. The `value` MUST be a single String.
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
[Extraction Rules for General Fields]
- company_name: Extract the names of the 'training company' and 'target company' explicitly written in text as they appear.
- company_name_normalized: From the extracted company name, completely remove terms like '(주)', '주식회사', '(유)', '유한회사', '(사)', '(재)' and ALL whitespaces to return only the pure company name as a string (e.g., "(주) 에이 비" -> "에이비"). If there are multiple companies, separate them with a comma (,).
- training_name: Extract the official name of the training exactly as written in the original text.
- training_content: Extract the detailed content or overview of the training exactly as written without summarization.
- training_date: Extract all original text representations of the training completion date.
- training_date_normalized: Normalize the training completion date into a "YYYY-MM-DD" string format to easily process in Python. Separate multiple dates with a comma (,). If impossible to determine, return "null".
- training_time: Extract all original text of the training time (e.g., "13:00~15:00", "8h").
- training_time_normalized: Based on the training time, normalize the actual start and end times into a "HH:MM~HH:MM" format. (DO NOT arbitrarily calculate the duration). If there are multiple times, combine them into a single string separated by commas (e.g., "09:00~12:00, 13:00~18:00").
- final_approval: Based on the context, find the final approval section (approval, confirmation, etc.). If there is a mark of a signature or stamp, return "Pass", otherwise "Fail".

**Table Fields Instruction
Table fields represent the attendee list found in the document.
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
[Extraction Rules for Table Fields]
- Extract data and tables from ALL pages.
- The `columns` array MUST be strictly fixed to the 7 items shown in the example above.
- The order of elements in the `data` array MUST exactly match the `columns` array.
- 참가자_이름 (Attendee Name): If the handwriting is illegible, do NOT force a guess. Output "[미상]".
- 참가자 서명 여부 (Attendee Signature Status): If there is any visual mark of a signature/stamp/check, output "Pass". If empty, output "Fail".
- 판독_상태 (Readability Status): Based on the visual form of the name, select ONLY ONE of the following 3 strings:
  (1) "PRINTED": Printed in computer font, clearly readable.
  (2) "HANDWRITTEN_CLEAR": Handwritten but clearly readable as a specific name.
  (3) "AMBIGUOUS": Handwritten but severely blurred, leaving room for misinterpretation, or processed as "[미상]" due to unreadability.
- 수강_교육명 (Attended Training Name): Extract the training name attended by the participant. If it is grouped and not explicitly stated per person, copy the main training name of the document.
- 수강_교육시간 (Attended Training Time): Extract the training time for the participant in "HH:MM~HH:MM" format or exactly as written. If grouped, copy it identically for each group member.

[Final Instructions - CRITICAL]
- Output ONLY valid, pure JSON text. Do NOT wrap it in markdown code blocks (e.g., ```json).
- LANGUAGE PRESERVATION: DO NOT translate any extracted Korean text into English. Preserve the original Korean text exactly as it appears in the image.
"""


```
