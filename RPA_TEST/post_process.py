import os
import json
import re
import traceback
from datetime import datetime
from utils.logger_utils import setup_module_logger

def post_process_and_save(in_params: dict, record: dict) -> str:
    logger = setup_module_logger(
        logger_name=in_params.get("logger_name", "POST_PROCESS"),
        log_dir=in_params.get("log_dir", "./logs"),
        log_level=in_params.get("log_level", logging.DEBUG)
    )

    try:
        for key in ["postprocess_output_dir"]:
            assert key in in_params, f"[ERROR] in_params에 '{key}'가 없습니다."
        for key in ["json_path", "FIID", "LINE_INDEX", "RECEIPT_INDEX", "COMMON_YN"]:
            assert key in record, f"[ERROR] record에 '{key}'가 없습니다."

        json_path = record["json_path"]
        output_dir = in_params["postprocess_output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"[ERROR] OCR JSON 파일이 없습니다: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc = data.get("analyzeResult", {}).get("documents", [{}])[0]
        fields = doc.get("fields", {})

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fiid = record["FIID"]
        line_index = record["LINE_INDEX"]
        receipt_index = record["RECEIPT_INDEX"]
        common_yn = record["COMMON_YN"]
        attach_file = record.get("ATTACH_FILE")

        summary = {
            "FIID": fiid,
            "LINE_INDEX": line_index,
            "RECEIPT_INDEX": receipt_index,
            "COMMON_YN": common_yn,
            "ATTACH_FILE": attach_file,
            "COUNTRY": fields.get("CountryRegion", {}).get("valueString"),
            "RECEIPT_TYPE": fields.get("MerchantCategory", {}).get("valueString"),
            "MERCHANT_NAME": fields.get("MerchantName", {}).get("valueString"),
            "MERCHANT_PHONE_NO": fields.get("MerchantPhoneNumber", {}).get("valueString"),
            "TRANSACTION_DATE": fields.get("TransactionDate", {}).get("valueDate"),
            "TRANSACTION_TIME": fields.get("TransactionTime", {}).get("valueString"),
            "TOTAL_AMOUNT": str(fields.get("Total", {}).get("valueCurrency", {}).get("amount")),
            "SUMTOTAL_AMOUNT": str(fields.get("Subtotal", {}).get("valueCurrency", {}).get("amount")),
            "TAX_AMOUNT": str(fields.get("TotalTax", {}).get("valueCurrency", {}).get("amount")),
            "RESULT_CODE": 200,
            "RESULT_MESSAGE": "SUCCESS",
            "CREATE_DATE": now_str,
            "UPDATE_DATE": now_str
        }

        item_list = []
        items_field = fields.get("Items", {})
        if "valueArray" in items_field:
            for idx, item in enumerate(items_field["valueArray"], start=1):
                obj = item.get("valueObject", {})
                item_list.append({
                    "FIID": fiid,
                    "LINE_INDEX": line_index,
                    "RECEIPT_INDEX": receipt_index,
                    "ITEM_INDEX": idx,
                    "ITEM_NAME": obj.get("Description", {}).get("valueString"),
                    "ITEM_QTY": str(obj.get("Quantity", {}).get("valueNumber")),
                    "ITEM_UNIT_PRICE": str(obj.get("Price", {}).get("valueCurrency", {}).get("amount")),
                    "ITEM_TOTAL_PRICE": str(obj.get("TotalPrice", {}).get("valueCurrency", {}).get("amount")),
                    "COMMON_YN": common_yn,
                    "CREATE_DATE": now_str,
                    "UPDATE_DATE": now_str
                })

        from post_process import extract_additional_fields_from_json
        extra = extract_additional_fields_from_json(json_path)
        summary["BIZ_NO"] = extra["BIZ_NO"]
        summary["DELIVERY_ADDR"] = extra["DELIVERY_ADDR"]
        for item in item_list:
            item["CONTENTS"] = extra["CONTENTS"]

        filename = f"post_{fiid}_{line_index}_{receipt_index}.json"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "items": item_list}, f, indent=2, ensure_ascii=False)

        return output_path

    except Exception as e:
        logger.error(f"후처리 실패: {traceback.format_exc()}")

        error_json_dir = in_params.get("error_json_dir", "./error_json")
        os.makedirs(error_json_dir, exist_ok=True)

        fail_filename = f"fail_{record.get('FIID')}_{record.get('LINE_INDEX')}_{record.get('RECEIPT_INDEX')}_{record.get('COMMON_YN')}.json"
        fail_path = os.path.join(error_json_dir, fail_filename)

        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump({
                "RESULT_CODE": "POST_ERR",
                "RESULT_MESSAGE": f"후처리 실패: {str(e)}",
                "FIID": record.get("FIID"),
                "LINE_INDEX": record.get("LINE_INDEX"),
                "RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
                "COMMON_YN": record.get("COMMON_YN")
            }, f, indent=2, ensure_ascii=False)

        raise RuntimeError(f"후처리 실패: {e}")


# 🧪 테스트 코드
if __name__ == "__main__":
    in_params = {
        "postprocess_output_dir": "./post_json"
    }
    record = {
        "json_path": "./test_json/공통영수증.jpg.json",
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "RECEIPT_INDEX": 1,
        "COMMON_YN": 1,
        "ATTACH_FILE": "GWS://e-sign/공통영수증.jpg"
    }

    result_path = post_process_and_save(in_params, record)
    print(f"✅ 후처리 결과 저장 완료: {result_path}")
