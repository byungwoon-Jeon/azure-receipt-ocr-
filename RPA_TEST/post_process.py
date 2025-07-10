import os
import json
import re
import traceback
from datetime import datetime


def extract_additional_fields_from_json(json_path: str) -> dict:
    """
    OCR JSON에서 사업자번호, 배달주소, 전체 텍스트 추출
    """
    result = {"BIZ_NO": None, "DELIVERY_ADDR": None, "CONTENTS": None}

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"[ERROR] JSON 파일이 존재하지 않습니다: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result["CONTENTS"] = data.get("analyzeResult", {}).get("content", "")
    lines = data.get("analyzeResult", {}).get("pages", [{}])[0].get("lines", [])

    for line in lines:
        content = line.get("content", "")

        if not result["BIZ_NO"]:
            match = re.search(r"사업자[ ]*번호.*?(\d{3}-\d{2}-\d{5}|\d{10})", content)
            if match:
                result["BIZ_NO"] = match.group(1)

        if not result["DELIVERY_ADDR"]:
            match = re.search(r"배달[ ]*주소[:：]?\s*(.*)", content)
            if match:
                result["DELIVERY_ADDR"] = match.group(1)

    return result


def post_process_and_save(in_params: dict, record: dict) -> str:
    """
    OCR 결과 JSON을 후처리하여 Summary + Item을 JSON으로 저장
    """
    try:
        # ─ 입력 검증 ─
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

        # 공통 필드
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fiid = record["FIID"]
        line_index = record["LINE_INDEX"]
        receipt_index = record["RECEIPT_INDEX"]
        common_yn = record["COMMON_YN"]
        attach_file = record.get("ATTACH_FILE")

        # Summary
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

        # Items
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

        # 추가 필드 추출
        extra = extract_additional_fields_from_json(json_path)
        summary["BIZ_NO"] = extra["BIZ_NO"]
        summary["DELIVERY_ADDR"] = extra["DELIVERY_ADDR"]
        for item in item_list:
            item["CONTENTS"] = extra["CONTENTS"]

        # 저장
        filename = f"post_{fiid}_{line_index}_{receipt_index}.json"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "items": item_list}, f, indent=2, ensure_ascii=False)

        return output_path

    except Exception as e:
        raise RuntimeError(f"[ERROR] 후처리 중 예외 발생: {e}\n{traceback.format_exc()}")


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
