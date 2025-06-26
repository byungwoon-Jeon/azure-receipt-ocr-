import json
import logging
import re
import sys
import traceback
from pathlib import Path

# ─ 공통 설정 ─
script_path = Path(__file__).resolve()
app_path = ""
for parent in script_path.parents:
    if parent.name in ("idp", "DEX", "PEX"):
        app_path = str(parent)
        break

if not app_path:
    raise FileNotFoundError("idp, DEX, PEX not found in path")

if app_path not in sys.path:
    sys.path.append(app_path)

from util import idp_utils

LOGGER_NAME = ""
LOG_LEVEL = logging.DEBUG
logger = idp_utils.setup_logger(LOGGER_NAME, LOG_LEVEL)


def extract_business_number(json_data: dict) -> str:
    lines = json_data.get("analyzeResult", {}).get("pages", [{}])[0].get("lines", [])
    for line in lines:
        text = line.get("content", "")
        if "사업자번호" in text or "사업자 번호" in text:
            match = re.search(r"\d{3}-\d{2}-\d{5}", text)
            if match:
                return match.group()
    full_text = json_data.get("analyzeResult", {}).get("content", "")
    match = re.search(r"\d{3}-\d{2}-\d{5}", full_text)
    return match.group() if match else ""


def extract_shipping_address(json_data: dict) -> str:
    lines = json_data.get("analyzeResult", {}).get("pages", [{}])[0].get("lines", [])
    for line in lines:
        text = line.get("content", "")
        if "배송지" in text:
            return text
    return ""


def extract_phone_number(json_data: dict) -> str:
    text = json_data.get("analyzeResult", {}).get("content", "")
    match = re.search(r"0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}", text)
    return match.group() if match else ""


def postprocess_receipt_json(in_params: dict) -> str:
    try:
        input_dir = Path(in_params["input_json_folder"])
        output_dir = Path(in_params["output_json_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)

        for json_file in input_dir.glob("*.json"):
            raw = json.loads(json_file.read_text(encoding="utf-8"))
            fields = raw.get("analyzeResult", {}).get("documents", [{}])[0].get("fields", {})

            out = {
                "country": fields.get("CountryRegion", {}).get("valueCountryRegion", ""),
                "receipt_type": fields.get("ReceiptType", {}).get("valueString", ""),
                "merchant_name": fields.get("MerchantName", {}).get("valueString", ""),
                "merchant_phone": extract_phone_number(raw),
                "transaction_date": fields.get("TransactionDate", {}).get("valueDate", ""),
                "transaction_time": fields.get("TransactionTime", {}).get("valueTime", ""),
                "subtotal": fields.get("Subtotal", {}).get("valueCurrency", {}).get("amount", None),
                "tax": fields.get("TotalTax", {}).get("valueCurrency", {}).get("amount", None),
                "total": fields.get("Total", {}).get("valueCurrency", {}).get("amount", None),
                "business_number": extract_business_number(raw),
                "shipping_address": extract_shipping_address(raw),
                "items": []
            }

            item_array = fields.get("Items", {}).get("valueArray", [])
            for item in item_array:
                obj = item.get("valueObject", {})
                out["items"].append({
                    "name": obj.get("Name", {}).get("valueString", ""),
                    "quantity": obj.get("Quantity", {}).get("valueNumber", None),
                    "unit_price": obj.get("Price", {}).get("valueCurrency", {}).get("amount", None),
                    "total_price": obj.get("TotalPrice", {}).get("valueCurrency", {}).get("amount", None),
                })

            save_path = output_dir / json_file.name
            save_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"후처리 완료: {save_path.name}")

        return str(output_dir)

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# ─ 테스트 ─
if __name__ == "__main__":
    test_params = {
        "input_json_folder": "result_output",
        "output_json_folder": "processed_output"
    }
    result = postprocess_receipt_json(test_params)
    print("후처리 완료 폴더:", result)
