import os
import json
import logging
import traceback
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from utils.logger_utils import setup_module_logger

def run_azure_ocr(in_params: dict, record: dict) -> dict:
    logger = setup_module_logger(
        logger_name=in_params.get("logger_name", "AZURE_OCR"),
        log_dir=in_params.get("log_dir", "./logs"),
        log_level=in_params.get("log_level", logging.DEBUG)
    )

    try:
        for key in ["azure_endpoint", "azure_key", "ocr_json_dir"]:
            assert key in in_params, f"[ERROR] in_params에 '{key}' 키가 없습니다."
        assert "file_path" in record, "[ERROR] record에 'file_path' 키가 없습니다."

        endpoint = in_params["azure_endpoint"]
        key = in_params["azure_key"]
        json_dir = in_params["ocr_json_dir"]
        os.makedirs(json_dir, exist_ok=True)

        file_path = record["file_path"]
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        with open(file_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", document=f)
            result = poller.result()
            result_dict = result.to_dict()

        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        json_filename = f"{base_filename}.ocr.json"
        json_path = os.path.join(json_dir, json_filename)

        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(result_dict, jf, ensure_ascii=False, indent=2)

        logger.info(f"OCR 성공 및 저장 완료: {json_path}")
        return result_dict

    except Exception as e:
        logger.error(f"OCR 실패: {traceback.format_exc()}")

        error_json_dir = in_params.get("error_json_dir", "./error_json")
        os.makedirs(error_json_dir, exist_ok=True)

        fail_filename = f"fail_{record.get('FIID')}_{record.get('LINE_INDEX')}_{record.get('RECEIPT_INDEX')}_{record.get('COMMON_YN')}.json"
        fail_path = os.path.join(error_json_dir, fail_filename)

        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump({
                "RESULT_CODE": "AZURE_ERR",
                "RESULT_MESSAGE": f"OCR 실패: {str(e)}",
                "FIID": record.get("FIID"),
                "LINE_INDEX": record.get("LINE_INDEX"),
                "RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
                "COMMON_YN": record.get("COMMON_YN")
            }, f, indent=2, ensure_ascii=False)

        return {
            "FIID": record.get("FIID"),
            "LINE_INDEX": record.get("LINE_INDEX"),
            "RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
            "COMMON_YN": record.get("COMMON_YN"),
            "RESULT_CODE": "AZURE_ERR",
            "RESULT_MESSAGE": f"OCR 실패: {e}"
        }

if __name__ == "__main__":
    from pprint import pprint

    in_params = {
        "azure_endpoint": "https://<your-endpoint>.cognitiveservices.azure.com/",
        "azure_key": "<your-api-key>",
        "ocr_json_dir": "C:/Users/quddn/Downloads/test/ocr_json"
    }

    record = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "RECEIPT_INDEX": 1,
        "COMMON_YN": 0,
        "file_path": "C:/Users/quddn/Downloads/test/cropped/라인아이템.png"
    }

    print("🧪 Azure OCR 테스트 시작...")
    result = run_azure_ocr(in_params, record)
    pprint(result)
