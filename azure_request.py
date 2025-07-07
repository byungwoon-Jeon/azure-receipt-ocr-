import os
import time
import requests
from dotenv import load_dotenv
from utils import setup_logger, ensure_dir, save_json
from datetime import datetime

# .env 로드
load_dotenv()

# 환경변수
ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
API_VERSION = "2024-02-29-preview"
MODEL_ID = "prebuilt-receipt"
LOG_DIR = './logs'

# 로거 설정
success_logger = setup_logger('azure_client_success', log_dir=LOG_DIR)
fail_logger = setup_logger('azure_client_failed', log_dir=LOG_DIR)

class AzureReceiptClient:
    def __init__(self):
        """Azure REST API 호출 클라이언트"""
        if not ENDPOINT or not KEY:
            fail_logger.error("Azure ENDPOINT 또는 KEY가 .env에 없습니다.")
            raise ValueError("필수 환경변수 없음")
        self.url = f"{ENDPOINT}/formrecognizer/documentModels/{MODEL_ID}:analyze?api-version={API_VERSION}"
        self.headers = {
            "Content-Type": "image/png",
            "Ocp-Apim-Subscription-Key": KEY
        }

    def analyze_receipt(self, image_path: str) -> dict:
        """
        이미지 파일을 Azure OCR API로 분석 요청

        Args:
            image_path (str): 이미지 경로

        Returns:
            dict: 분석 결과 JSON (실패 시 None)
        """
        try:
            with open(image_path, "rb") as f:
                start_time = datetime.now()
                response = requests.post(self.url, headers=self.headers, data=f)
                if response.status_code != 202:
                    fail_logger.error(f"[실패] 분석 요청 실패: {image_path}, 응답: {response.text}")
                    return None

                operation_url = response.headers.get("operation-location")
                if not operation_url:
                    fail_logger.error(f"[실패] operation-location 없음: {image_path}")
                    return None

                # 결과 polling
                for attempt in range(20):  # 최대 20초 대기
                    poll_response = requests.get(operation_url, headers=self.headers)
                    poll_result = poll_response.json()
                    status = poll_result.get("status")

                    if status == "succeeded":
                        elapsed = (datetime.now() - start_time).total_seconds()
                        success_logger.info(f"[성공] 분석 완료: {image_path}, 소요 시간: {elapsed:.2f}초")
                        return poll_result
                    elif status in ("failed", "error"):
                        fail_logger.error(f"[실패] 분석 실패: {image_path}, 상태: {status}")
                        return None

                    time.sleep(1)

                fail_logger.warning(f"[경고] 분석 시간 초과: {image_path}")
                return None

        except Exception as e:
            fail_logger.exception(f"[예외] analyze_receipt 실패: {image_path} - {e}")
            return None

    def analyze_folder(self, input_dir: str, output_dir: str):
        """
        폴더 내 PNG 이미지 모두 분석하고 결과 저장

        Args:
            input_dir (str): 이미지 폴더
            output_dir (str): 결과 JSON 저장 폴더
        """
        try:
            ensure_dir(output_dir, success_logger)
            files = os.listdir(input_dir)

            for filename in files:
                if filename.lower().endswith('.png'):
                    input_path = os.path.join(input_dir, filename)
                    output_filename = os.path.splitext(filename)[0] + ".json"
                    output_path = os.path.join(output_dir, output_filename)

                    if os.path.exists(output_path):
                        success_logger.info(f"[스킵] 이미 처리된 파일 : {filename}")
                        continue

                    result = self.analyze_receipt(input_path)

                    if result:
                        save_json(result, output_path, success_logger)
                    else:
                        fail_logger.warning(f"[경고] 결과 없음 : {filename}")

            success_logger.info(f"[완료] 폴더 분석 및 저장 완료 : {input_dir} → {output_dir}")

        except Exception as e:
            fail_logger.exception(f"[예외] analyze_folder 실패: {e}")

# =============================================
# 메인 진입점
# =============================================
if __name__ == "__main__":
    client = AzureReceiptClient()
    client.analyze_folder('./processed_images', './results/json')