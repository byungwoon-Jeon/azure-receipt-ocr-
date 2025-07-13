import os
import json
import logging
import traceback
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

logger = logging.getLogger("AZURE_OCR")

def run_azure_ocr(in_params: dict, record: dict) -> dict:
    """
    Call Azure Form Recognizer OCR on the given image file (from record['file_path']).
    Returns the OCR result as a dictionary. If OCR fails, writes an error JSON and 
    returns a dict with RESULT_CODE and error message (including FIID, LINE_INDEX, etc.).
    """
    try:
        # Required config values for Azure OCR
        assert "azure_endpoint" in in_params, "[ERROR] 'azure_endpoint' is missing in in_params."
        assert "azure_key" in in_params, "[ERROR] 'azure_key' is missing in in_params."
        assert "ocr_json_dir" in in_params, "[ERROR] 'ocr_json_dir' is missing in in_params."
        assert "file_path" in record, "[ERROR] record is missing 'file_path'."

        endpoint = in_params["azure_endpoint"]
        key = in_params["azure_key"]
        json_dir = in_params["ocr_json_dir"]
        os.makedirs(json_dir, exist_ok=True)

        file_path = record["file_path"]
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

        # Call Azure OCR service
        with open(file_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", document=f)
            result = poller.result()
            result_dict = result.to_dict()

        # Save the OCR result to a JSON file
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        json_filename = f"{base_filename}.ocr.json"
        json_path = os.path.join(json_dir, json_filename)
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(result_dict, jf, ensure_ascii=False, indent=2)

        logger.info(f"OCR 성공 및 JSON 저장: {json_path}")
        return result_dict

    except Exception as e:
        logger.error(f"OCR 실패: {traceback.format_exc()}")

        # On failure, save an error JSON with details
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
                "COMMON_YN": record.get("COMMON_YN"),
                "GUBUN": record.get("GUBUN")
            }, f, ensure_ascii=False, indent=2)

        # Return a dict indicating failure (including GUBUN for completeness)
        return {
            "FIID": record.get("FIID"),
            "LINE_INDEX": record.get("LINE_INDEX"),
            "RECEIPT_INDEX": record.get("RECEIPT_INDEX"),
            "COMMON_YN": record.get("COMMON_YN"),
            "GUBUN": record.get("GUBUN"),
            "RESULT_CODE": "AZURE_ERR",
            "RESULT_MESSAGE": f"OCR 실패: {e}"
        }

if __name__ == "__main__":
    from pprint import pprint

    # ✅ 테스트 입력 파라미터 설정
    in_params = {
        "azure_endpoint": "https://<your-resource>.cognitiveservices.azure.com/",  # ← 실제 엔드포인트로 수정
        "azure_key": "<your-azure-key>",                                           # ← 실제 키로 수정
        "ocr_json_dir": "./test_ocr_json",                                         # OCR 결과 저장 경로
        "error_json_dir": "./test_error_json"                                      # 실패 시 에러 파일 저장 경로
    }

    # ✅ 테스트 이미지 (사전에 YOLO+전처리된 PNG 이미지 사용 권장)
    record = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "RECEIPT_INDEX": 1,
        "COMMON_YN": 0,
        "GUBUN": "Y",
        "file_path": "./test_cropped/sample_receipt.png"  # 실제 영수증 이미지 경로로 교체
    }

    print("🧪 run_azure_ocr() 테스트 시작")
    result = run_azure_ocr(in_params, record)

    print("\n📄 결과:")
    pprint(result)
