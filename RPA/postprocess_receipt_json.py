import logging
import sys
import traceback
from pathlib import Path
import json

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


def postprocess_receipt_json(in_params: dict) -> str:
    """
    Azure receipt 모델로 생성된 JSON들을 읽어 
    지정된 필드를 추출/재구성하여 새 JSON 파일로 저장

    Args:
        in_params (dict): {
            "input_json_folder": 원본 JSON 폴더 경로,
            "output_json_folder": 가공된 JSON 저장 폴더 경로
        }

    Returns:
        str: 저장된 가공 JSON 폴더 경로
    """
    try:
        input_dir = Path(in_params["input_json_folder"])
        output_dir = Path(in_params["output_json_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)

        for js_file in input_dir.glob("*.json"):
            data = json.loads(js_file.read_text(encoding="utf-8"))
            doc = data.get("analyzeResult", {}).get("documentResults", [{}])[0]

            out = {
                "country": doc.get("countryRegion", ""),
                "receipt_type": doc.get("receiptType", ""),
                "merchant_name": doc.get("merchantName", ""),
                "merchant_phone_number": doc.get("merchantPhoneNumber", ""),
                "transaction_datetime": (
                    f"{doc.get('transactionDate','')}"
                    f"{' ' + doc.get('transactionTime','') if doc.get('transactionTime') else ''}"
                ),
                "total_amount": doc.get("total", None),
                "subtotal_amount": doc.get("subtotal", None),
                "tax_amount": doc.get("tax", doc.get("totalTax", None)),
                "shipping_address": "",      # 기본 제공 안됨
                "business_registration_number": "",  # 기본 제공 안됨
                "items": []
            }

            for item in doc.get("items", []):
                out["items"].append({
                    "name": item.get("Name") or item.get("Description", ""),
                    "quantity": item.get("Quantity", None),
                    "unit_price": item.get("Price", None),
                    "total_price": item.get("TotalPrice", None)
                })

            save_path = output_dir / js_file.name
            save_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"후처리 저장: {save_path.name}")

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
    print("후처리 결과 폴더:", result)