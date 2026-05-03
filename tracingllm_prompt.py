# 1. System Prompt: Define Persona and Core Principles in English for better adherence.
SYSTEM_PROMPT = """You are a world-class expert in document processing and data structuring. 
Your goal is to extract text from document images with 100% accuracy and return it in a structured format that Python backend systems can parse immediately."""

# 2. Document Prompt (Detail Prompt): Use English for logic/structure, but specify Korean for content.
DOCUMENT_PROMPT_TEMPLATE = """
Analyze the provided educational report image and extract requested data precisely.

[Core Principles & Special Instructions]
1. Hand-written Text & Hallucination Defense:
   - Be extremely cautious with hand-written names. You tend to force-match messy strokes into common names; DO NOT do this.
   - If a name is illegible or can be read as multiple names (e.g., looks like both "A" and "B"), output "[Unknown]".
   - NEVER guess or hallucinate. Safety is top priority.
2. Self-Correction Step:
   - After extraction, double-check the values against the image pixels. 
   - If there is any visual ambiguity, overwrite the value with "[Unknown]".
3. Signature (Sign) Handling:
   - Do not try to read text in signature fields. 
   - Simply determine if any visual mark (sign, stamp, check) exists: return 'true' if exists, 'false' if empty.
4. Time Extraction:
   - Extract the time text exactly as written (e.g., "13:00~15:00"). 
   - DO NOT calculate duration or convert format.
5. Strict JSON Output:
   - Output ONLY valid raw JSON text without any greetings, markdown blocks (```json), or explanations.

[Output JSON Schema]
Follow this structure strictly. 
- bounding_box: [ymin, xmin, ymax, xmax] normalized to 1000x1000.

{
  "general_field": [
    {
      "field_name": "training_name",
      "value": "Extracted Training Name (Keep Korean)",
      "confidence": 0.95,
      "bounding_box": [10, 10, 50, 200]
    },
    {
      "field_name": "training_time",
      "value": "Extracted Time Text",
      "confidence": 0.99,
      "bounding_box": [60, 10, 100, 200]
    }
  ],
  "table_field": {
    "attendee_list": [
      {
        "attendee_name": {"value": "Extracted Name (Keep Korean or [Unknown])", "confidence": 0.8, "bounding_box": [..]},
        "is_signed": {"value": true, "confidence": 0.99, "bounding_box": [..]}
      }
    ]
  }
}

[Target Fields Description (Target Specifics)]
{target_fields_description}
"""
