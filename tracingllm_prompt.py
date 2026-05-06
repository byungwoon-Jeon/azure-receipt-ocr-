```python
# 1. System Instruction
SYSTEM_INSTRUCTION = """You are an expert in extracting meaningful data from given documents. 
Your task is to extract essential data from the document into a strict JSON format. 
This role remains active until the task is completed."""

# 2. Main Document Prompt
DOCUMENT_PROMPT_TEMPLATE = """You are provided with a training log (training result report) document.
Your JSON output MUST strictly follow the structure below.

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
        { "page_number": 0, "name": "training_name", "value": "str" },
        { "page_number": 0, "name": "training_content", "value": "str" },
        { "page_number": 0, "name": "training_date", "value": "str" },
        { "page_number": 0, "name": "training_date_normalized", "value": "str" },
        { "page_number": 0, "name": "training_time", "value": "str" },
        { "page_number": 0, "name": "training_duration_minutes", "value": "str" },
        { "page_number": 0, "name": "final_approval", "value": "str" }
    ]
}
'''
[Extraction Rules for General Fields]
- company_name: Extract the names of the 'training company' and 'target company' explicitly written in text. DO NOT infer the name from a logo if there is no text. If there are multiple companies, return them as a comma-separated string (e.g., "A회사, B교육센터").
- training_name: Extract the official name of the training exactly as written.
- training_content: Extract the detailed content or overview of the training exactly as written in the original text. Do not summarize.
- training_date: Extract the original text of the training completion date (e.g., "26년 5월 1일", "05/01").
- training_date_normalized: Normalize the extracted training date into a "YYYY-MM-DD" string format. If it cannot be determined, return the string "null".
- training_time: Extract the original text of the training time (e.g., "13:00~15:00", "8h").
- training_duration_minutes: Based on the extracted training time, calculate the total duration and normalize it as a string representing the number of 'minutes' (e.g., "120", "480"). If it cannot be determined, return the string "null".
- final_approval: Based on the context, locate the final approval section (e.g., approval, confirmation). If there is any mark of a signature, stamp, or sign in that section, return "Pass". Otherwise, return "Fail".

**Table Fields Instruction
Table fields represent the attendee list found in the document, which typically includes the attendee's name, signature, etc.
'''json
{
    "table_fields": [
        {
            "table_name": "attendee_list",
            "columns": ["row_number", "page_number", "참가자_이름", "참가자 서명 여부", "이름에 대한 신뢰도", "손글씨 여부"],
            "data": [["1", "1", "홍길동", "Pass", "0.5", "true"]],
            "data_length": 0
        }
    ]
}
'''
[Extraction Rules for Table Fields]
- Extract data and tables from ALL pages.
- The `columns` array MUST be strictly fixed to the 6 items shown in the example above.
- The `data` field contains detailed values for each column. The order of elements in each inner array MUST exactly match the `columns` array.
- 참가자_이름 (Attendee Name): If the handwriting is completely illegible, do NOT force a guess. Output "[미상]".
- 참가자 서명 여부 (Attendee Signature Status): If there is any visual mark of a signature, stamp, or check, output "Pass". If completely empty, output "Fail".
- 이름에 대한 신뢰도 (Confidence in Name): DO NOT use your own arbitrary confidence. Assign a score based strictly on the following objective criteria as a string:
  (1) "1.0": Computer-printed text or extremely clear, unmistakable block-letter handwriting.
  (2) "0.5": Messy handwriting where strokes are blurred, overlapping, or could potentially be read as two or more different names.
  (3) "0.0": Completely illegible and processed as "[미상]".
- 손글씨 여부 (Handwriting Status): Judge based on visual characteristics. If the text crosses the table border, has irregular spacing/size, or shows variations in pen ink thickness/strokes, you MUST output "true". If it is perfectly aligned like a computer font, output "false".

[Final Instructions - CRITICAL]
- Output ONLY valid, pure JSON text. Do NOT wrap it in markdown code blocks (e.g., ```json). Do NOT add any explanations.
- LANGUAGE PRESERVATION: DO NOT translate any extracted Korean text into English. Preserve the original Korean text exactly as it appears in the image.
"""


```
