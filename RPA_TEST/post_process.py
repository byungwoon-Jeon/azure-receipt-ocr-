import os
import json
import re
import logging
import traceback
from datetime import datetime

logger = logging.getLogger("POST_PROCESS")

def post_process_and_save(in_params: dict, record: dict) -> str:
    """
    Azure OCR 결과 JSON 데이터를 후처리하여 요약(summary) 정보와 항목(item) 리스트를 추출하고, 이들을 하나의 JSON 파일로 저장합니다.
    인식된 필드 값을 정리하고, 필요한 경우 추가 필드를 추출하여 summary와 item 리스트를 생성합니다.

    입력:
    - in_params (dict): 후처리 동작에 필요한 설정값 (postprocess_output_dir 등)과 경로 정보.
    - record (dict): 후처리 대상 정보를 담은 딕셔너리. OCR 결과 JSON 경로(json_path)와 식별자 정보(FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN 등)를 포함해야 합니다.

    출력:
    - str: 생성된 후처리 결과 JSON 파일의 경로.

    예외 처리:
    후처리 중 오류 발생 시 로그를 남기고 오류 내용을 담은 JSON 파일을 생성한 뒤, RuntimeError를 발생시킵니다.
    """
    logger.info("[시작] post_process_and_save")

    try:
        # 필수 입력값 검사
        assert "postprocess_output_dir" in in_params, "[ERROR] 'postprocess_output_dir' 미지정"
        for key in ["json_path", "FIID", "LINE_INDEX", "RECEIPT_INDEX", "COMMON_YN"]:
            assert key in record, f"[ERROR] '{key}' 필드 없음"

        json_path = record["json_path"]
        output_dir = in_params["postprocess_output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"OCR JSON 파일이 존재하지 않음: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc = data.get("analyzeResult", {}).get("documents", [{}])[0]
        fields = doc.get("fields", {}) if isinstance(doc, dict) else {}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fiid = record["FIID"]
        line_index = record["LINE_INDEX"]
        receipt_index = record["RECEIPT_INDEX"]
        common_yn = record["COMMON_YN"]
        attach_file = record.get("ATTACH_FILE")
        gubun = record.get("GUBUN")

        summary = {
            "FIID": fiid,
            "LINE_INDEX": line_index,
            "RECEIPT_INDEX": receipt_index,
            "COMMON_YN": common_yn,
            "GUBUN": gubun,
            "ATTACH_FILE": attach_file,
            "COUNTRY": fields.get("CountryRegion", {}).get("valueCountryRegion"),
            "RECEIPT_TYPE": fields.get("MerchantCategory", {}).get("valueString"),
            "MERCHANT_NAME": fields.get("MerchantName", {}).get("valueString"),
            "MERCHANT_PHONE_NO": fields.get("MerchantPhoneNumber", {}).get("valueString"),
            "DELIVERY_ADDR": None,
            "TRANSACTION_DATE": fields.get("TransactionDate", {}).get("valueDate"),
            "TRANSACTION_TIME": fields.get("TransactionTime", {}).get("valueTime"),
            "TOTAL_AMOUNT": str(fields.get("Total", {}).get("valueCurrency", {}).get("amount")),
            "SUMTOTAL_AMOUNT": str(fields.get("Subtotal", {}).get("valueCurrency", {}).get("amount")),
            "TAX_AMOUNT": str(fields.get("TotalTax", {}).get("valueCurrency", {}).get("amount")),
            "BIZ_NO": None,
            "RESULT_CODE": 200,
            "RESULT_MESSAGE": "SUCCESS",
            "CREATE_DATE": now_str,
            "UPDATE_DATE": now_str
        }

        # 라인 아이템 추출
        item_list = []
        items_field = fields.get("Items", {})
        if isinstance(items_field, dict) and "valueArray" in items_field:
            for idx, item in enumerate(items_field["valueArray"], start=1):
                obj = item.get("valueObject", {}) if item else {}
                item_list.append({
                    "FIID": fiid,
                    "LINE_INDEX": line_index,
                    "RECEIPT_INDEX": receipt_index,
                    "ITEM_INDEX": idx,
                    "ITEM_NAME": obj.get("Description", {}).get("valueString"),
                    "ITEM_QTY": str(obj.get("Quantity", {}).get("valueNumber")) if obj.get("Quantity") else None,
                    "ITEM_UNIT_PRICE": str(obj.get("Price", {}).get("valueCurrency", {}).get("amount")) if obj.get("Price") else None,
                    "ITEM_TOTAL_PRICE": str(obj.get("TotalPrice", {}).get("valueCurrency", {}).get("amount")) if obj.get("TotalPrice") else None,
                    "CONTENTS": json.dumps(obj, ensure_ascii=False)
                })

        # 결과 저장
        result_json = {
            "summary": summary,
            "items": item_list
        }

        output_filename = f"{fiid}_{line_index}_{receipt_index}_post.json"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(result_json, out_f, ensure_ascii=False, indent=2)

        logger.info(f"[완료] 후처리 결과 저장: {output_path}")
        logger.info("[종료] post_process_and_save")
        return output_path

    except Exception as e:
        logger.error(f"[ERROR] 후처리 실패: {e}")
        traceback.print_exc()

        error_path = os.path.join(in_params.get("error_json_dir", "./error_json"), f"fail_{record['FIID']}_{record['LINE_INDEX']}.json")
        os.makedirs(os.path.dirname(error_path), exist_ok=True)
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump({
                "FIID": record.get("FIID"),
                "LINE_INDEX": record.get("LINE_INDEX"),
                "RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
                "RESULT_CODE": "POST_ERR",
                "RESULT_MESSAGE": str(e)
            }, f, ensure_ascii=False, indent=2)

        return error_path

if __name__ == "__main__":
    from pprint import pprint

    # ✅ 테스트 파라미터
    in_params = {
        "postprocess_output_dir": "./test_postprocess_json",  # 후처리 결과 저장 위치
        "error_json_dir": "./test_error_json"                 # 실패 시 에러 JSON 저장 위치
    }

    # ✅ 테스트용 OCR JSON을 가진 record
    record = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "RECEIPT_INDEX": 1,
        "COMMON_YN": 0,
        "GUBUN": "Y",
        "ATTACH_FILE": "https://dummy-url/receipt.png",
        "json_path": "./test_ocr_json/sample_receipt.ocr.json"  # 실제 OCR JSON 경로로 바꿔줘
    }

    try:
        print("🧪 post_process_and_save() 테스트 시작")
        output_path = post_process_and_save(in_params, record)

        print(f"\n📁 생성된 파일 경로: {output_path}")
        with open(output_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)
            print("\n📄 요약 데이터:")
            pprint(result_data["summary"])
            print("\n📦 아이템 데이터:")
            pprint(result_data["items"])

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
