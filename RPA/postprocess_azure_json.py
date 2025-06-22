import json
import os
from datetime import datetime

def postprocess_azure_json(json_path: str, output_dir: str) -> dict:
    """
    Azure OCR 결과 JSON에서 fields 항목만 파싱하여 저장

    Parameters
    ----------
    json_path : str
        Azure OCR 결과 파일 경로 (.json)
    output_dir : str
        후처리 결과 저장 디렉토리

    Returns
    -------
    dict
        {
            "success": True/False,
            "saved_path": 저장된 파일 경로,
            "error": None or 에러 메시지
        }
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        fields = data.get("documents", [{}])[0].get("fields", {})
        cleaned_data = {}

        for field_name, field_data in fields.items():
            if "value" in field_data:
                cleaned_data[field_name] = field_data["value"]
            elif "content" in field_data:  # Fallback
                cleaned_data[field_name] = field_data["content"]

        # 저장
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"{base_name}_cleaned_{timestamp}.json"
        save_path = os.path.join(output_dir, save_name)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "saved_path": save_path, "error": None}

    except Exception as e:
        return {"success": False, "saved_path": None, "error": str(e)}
