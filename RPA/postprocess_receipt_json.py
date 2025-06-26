import json
import logging
import re
import sys
import traceback
from pathlib import Path

# 공통 설정
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


def extract_business_number(text: str) -> str:
    match = re.search(r"사업자\s*번호[:\s]*([\d\-]{10,})", text)
    return match.group(1).strip() if match else ""


def extract_shipping_address(text: str) -> str:
    for line in text.splitlines():
        if "배송지" in line:
            return line.strip()
    return ""


def extract_phone_number(text: str) -> str:
    match = re.search(r"0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}", text)
    return match.group(0).strip() if match else ""


def postprocess_receipt_json(in_params: dict) -> str:
    try:
        input_dir = Path(in_params["input_json_folder"])
        output_dir = Path(in_params["output_json_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)

        for file in input_dir.glob("*.json"):
            raw = json.loads(file.read_text(encoding="utf-8"))
            fields = raw.get("analyzeResult", {}).get("documents", [{}])[0].get("fields", {})
            ocr_text = raw.get("analyzeResult", {}).get("content", "")

            out = {
                "country": fields.get("CountryRegion", {}).get("valueCountryRegion", ""),
                "receipt_type": fields.get("ReceiptType", {}).get("valueString", ""),
                "merchant_name": fields.get("MerchantName", {}).get("valueString", ""),
                "transaction_date": fields.get("TransactionDate", {}).get("valueDate", ""),
                "transaction_time": fields.get("TransactionTime", {}).get("valueTime", ""),
                "subtotal": fields.get("Subtotal", {}).get("valueCurrency", {}).get("amount", None),
                "tax": fields.get("TotalTax", {}).get("valueCurrency", {}).get("amount", None),
                "total": fields.get("Total", {}).get("valueCurrency", {}).get("amount", None),
                "merchant_phone": extract_phone_number(ocr_text),
                "business_number": extract_business_number(ocr_text),
                "shipping_address": extract_shipping_address(ocr_text),
                "items": []
            }

            # 품목 리스트
            for item in fields.get("Items", {}).get("valueArray", []):
                obj = item.get("valueObject", {})
                out["items"].append({
                    "name": obj.get("Name", {}).get("valueString", ""),
                    "quantity": obj.get("Quantity", {}).get("valueNumber", None),
                    "unit_price": obj.get("Price", {}).get("valueCurrency", {}).get("amount", None),
                    "total_price": obj.get("TotalPrice", {}).get("valueCurrency", {}).get("amount", None),
                })

            output_file = output_dir / file.name
            output_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"후처리 저장: {output_file.name}")

        return str(output_dir)

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# 테스트
if __name__ == "__main__":
    test_params = {
        "input_json_folder": "result_output",       # Azure 결과 폴더
        "output_json_folder": "processed_output"    # 후처리 저장 폴더
    }
    result = postprocess_receipt_json(test_params)
    print("후처리 완료 폴더:", result)