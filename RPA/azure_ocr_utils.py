import os
import json
from datetime import datetime
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# ──────────────── 로그 훅 예시 ────────────────
def log_info(msg):
    pass

def log_error(msg):
    pass
# ─────────────────────────────────────────────


def analyze_with_azure(
    image_path: str,
    output_dir: str,
    endpoint: str,
    key: str
) -> dict:
    """
    Azure Document Intelligence - Prebuilt Receipt 분석 및 JSON 저장

    Parameters
    ----------
    image_path : str
        분석할 이미지 경로 (.png)
    output_dir : str
        분석 결과(JSON) 저장할 디렉터리
    endpoint : str
        Azure 엔드포인트 URL
    key : str
        Azure API Key

    Returns
    -------
    dict
        {
            "success": True/False,
            "saved_path": ...,   # JSON 파일 경로
            "error": None or 에러 메시지
        }
    """
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 클라이언트 초기화
        client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

        with open(image_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", document=f)
            result = poller.result()

        # 파일 저장 경로 설정
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        filename = f"{base_name}_{timestamp}.json"
        save_path = os.path.join(output_dir, filename)

        # JSON 저장
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        # [HOOK] 저장 성공 로그
        # log_info(f"[OCR] 저장 완료: {save_path}")

        return {"success": True, "saved_path": save_path, "error": None}

    except Exception as e:
        # log_error(f"[OCR] 오류 발생: {e}")
        return {"success": False, "saved_path": None, "error": str(e)}
