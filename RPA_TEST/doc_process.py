import os
import json
import logging
import traceback
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

def run_azure_ocr(in_params: dict, record: dict) -> dict:
    """
    Azure Document Intelligence로 OCR 수행 후 결과 JSON 저장

    Args:
        in_params (dict): {
            "azure_endpoint": Azure 엔드포인트,
            "azure_key": Azure 키,
            "ocr_json_dir": JSON 저장 경로
        }
        record (dict): {
            "FIID", "LINE_INDEX", "RECEIPT_INDEX", "COMMON_YN", "file_path"
        }

    Returns:
        dict: OCR JSON 데이터 (또는 에러 정보)
    """
    logger = logging.getLogger("AZURE_OCR")
    logger.setLevel(logging.DEBUG)

    try:
        # ─ 입력 검증 ─
        for key in ["azure_endpoint", "azure_key", "ocr_json_dir"]:
            assert key in in_params, f"[ERROR] in_params에 '{key}' 키가 없습니다."
        assert "file_path" in record, "[ERROR] record에 'file_path' 키가 없습니다."

        endpoint = in_params["azure_endpoint"]
        key = in_params["azure_key"]
        json_dir = in_params["ocr_json_dir"]
        os.makedirs(json_dir, exist_ok=True)

        file_path = record["file_path"]
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        # ─ Azure OCR 요청 ─
        with open(file_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", document=f)
            result = poller.result()
            result_dict = result.to_dict()

        # ─ JSON 저장 ─
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        json_filename = f"{base_filename}.ocr.json"
        json_path = os.path.join(json_dir, json_filename)

        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(result_dict, jf, ensure_ascii=False, indent=2)

        logger.info(f"OCR 성공 및 저장 완료: {json_path}")
        return result_dict

    except Exception as e:
        logger.error(f"OCR 실패: {traceback.format_exc()}")
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
