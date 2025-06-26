import logging
import sys
import traceback
from pathlib import Path
import requests
import json

# ─ 공통 세팅 ─
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


def analyze_cropped_images_with_azure(in_params: dict) -> str:
    """
    크롭된 이미지들을 Azure 모델에 보내 결과를 JSON 파일로 저장

    Args:
        in_params (dict): {
            "cropped_image_path": 크롭 이미지 폴더,
            "result_json_path": JSON 저장 폴더,
            "azure_endpoint": Azure 엔드포인트 URL,
            "azure_key": Azure API 키
        }

    Returns:
        str: JSON 결과 저장 폴더 경로
    """
    try:
        input_dir = Path(in_params["cropped_image_path"])
        output_dir = Path(in_params["result_json_path"])
        output_dir.mkdir(parents=True, exist_ok=True)

        endpoint = in_params["azure_endpoint"]
        key = in_params["azure_key"]

        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/octet-stream"
        }

        for image_path in input_dir.glob("*.png"):
            with open(image_path, "rb") as img_file:
                response = requests.post(
                    url=f"{endpoint}/formrecognizer/documentModels/prebuilt-receipt:analyze?api-version=2024-02-29",
                    headers=headers,
                    data=img_file
                )

            if response.status_code != 200:
                logger.warning(f"분석 실패: {image_path.name} - {response.status_code}")
                continue

            result_json = response.json()
            json_save_path = output_dir / f"{image_path.stem}.json"
            with open(json_save_path, "w", encoding="utf-8") as f:
                json.dump(result_json, f, ensure_ascii=False, indent=2)

            logger.info(f"분석 완료: {json_save_path.name}")

        return str(output_dir)

    except Exception as e:
        logger.exception(e)
        return traceback.format_exc()


# ─ 테스트 ─
if __name__ == "__main__":
    test_params = {
        "cropped_image_path": "cropped_output",
        "result_json_path": "result_output",
        "azure_endpoint": "https://<your-resource-name>.cognitiveservices.azure.com",
        "azure_key": "<your-azure-key>"
    }
    result = analyze_cropped_images_with_azure(test_params)
    print("JSON 결과 폴더:", result)