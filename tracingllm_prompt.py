```python
# 1. System Instruction
SYSTEM_INSTRUCTION = """You are an expert at extracting meaningful data from documents. 
Your task is to extract essential data in the specified JSON format. 
This role remains valid until the completion of this task."""

# 2. Document Prompt (Main Prompt)
DOCUMENT_PROMPT_TEMPLATE = """You are provided with an Educational Report (Training Log) document.
Your goal is to extract data into a JSON structure as defined below.

[JSON Structure]
{
    "extract_pages_range": [1, <EXT_PAGE_UNITS>],
    "general_fields": [],
    "table_fields": []
}

** General Fields Instruction
The structure for general_fields is as follows:
{
    "general_fields": [
        {
            "page_number": 0,
            "name": "training_name",
            "value": "str"
        },
        {
            "page_number": 0,
            "name": "training_time",
            "value": "str"
        },
        {
            "page_number": 0,
            "name": "training_date",
            "value": "str"
        },
        {
            "page_number": 0,
            "name": "training_content",
            "value": "str"
        }
    ]
}
- training_time: Extract the time information exactly as it appears. It could be in "hh:mm~hh:mm" format or duration format like "8h" or "8시간". Do not convert or calculate.
- training_content: Extract the detailed description or summary of the training. Preserve the original text as much as possible without summarization.
- IMPORTANT: All "value" fields must keep the original language (Korean) found in the document.

** Table Fields Instruction
The structure for table_fields is as follows:
{
    "table_fields": [
        {
            "table_name": "attendee_list",
            "columns": ["row_number", "page_number", "participant_name", "signature_status", "name_confidence", "is_handwritten"],
            "data": [["str", "str", "str", "str", "str", "str"]],
            "data_length": 0
        }
    ]
}
- The table represents the attendee list, including names and signatures.
- Extract data and tables from ALL pages.
- Columns are fixed as: row_number, page_number, participant_name, signature_status, name_confidence, is_handwritten.
- signature_status: Return "Pass" if there is a signature, stamp, or mark; otherwise, return "Fail".
- name_confidence: Provide a score from 0.0 to 1.0 based on the legibility of the name. If illegible, use "[Unknown]" for the name and 0.0 for confidence.
- is_handwritten: Return "true" if the name is handwritten, "false" if it is printed text.
- data_length: The total count of rows extracted.

[Final Instructions]
- Output ONLY the raw JSON text. 
- Do NOT include markdown code blocks (```json), headers, or any conversational text.
- If a value is missing or unrecognizable, use null or "[Unknown]".
"""

```
