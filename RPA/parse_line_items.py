import json
from typing import List, Dict, Any
from pathlib import Path

def parse_line_items(in_params: dict) -> List[Dict[str, Any]]:
    """
    Extracts itemized data from the receipt JSON for RPA_CCR_LINE_ITEMS table format.

    Args:
        in_params (dict): Input dictionary containing all required keys including:
                          - json_path (str): Path to the Azure OCR JSON file
                          - FIID, LINE_INDEX, RECEIPT_INDEX (any): identifiers

    Returns:
        List[dict]: Extracted itemized data
    """
    # Extract necessary identifiers
    fiid = in_params.get("FIID")
    line_index = in_params.get("LINE_INDEX")
    receipt_index = in_params.get("RECEIPT_INDEX")

    # Load JSON
    json_path = in_params.get("json_path")
    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    documents = json_data.get("analyzeResult", {}).get("documents", [])
    if not documents:
        return []

    doc = documents[0]
    items = doc.get("fields", {}).get("Items", {}).get("valueArray", [])
    lines = doc.get("lines", [])

    # Collect full content lines
    contents = "\n".join(line.get("content", "") for line in lines)

    # Parse each item
    results = []
    for idx, item in enumerate(items):
        obj = item.get("valueObject", {})
        entry = {
            "FIID": fiid,
            "LINE_INDEX": line_index,
            "RECEIPT_INDEX": receipt_index,
            "ITEM_INDEX": idx,
            "ITEM_NAME": obj.get("Description", {}).get("valueString", ""),
            "ITEM_QTY": obj.get("Quantity", {}).get("valueNumber", None),
            "ITEM_UNIT_PRICE": None,  # Not provided directly
            "ITEM_TOTAL_PRICE": obj.get("TotalPrice", {}).get("valueCurrency", {}).get("amount", None),
            "CONTENTS": contents,
        }
        results.append(entry)

    return results

# Test with a sample path (disabled here; will be run outside the notebook)
# parse_line_items({
#     "FIID": "A001",
#     "LINE_INDEX": 1,
#     "RECEIPT_INDEX": 1,
#     "json_path": "/mnt/data/receipt-with-tips.jpg.json"
# })


