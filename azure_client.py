import os
import json
import datetime
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from logger_utils import setup_logger

# .env 불러오기
load_dotenv()

# 환경변수 읽기
endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

# 로그 설정
logger = setup_logger('azure_client')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Created directory: {path}")

class AzureReceiptClient:
    def __init__(self):
        self.client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

    def analyze_receipt(self, image_path):
        try:
            with open(image_path, "rb") as f:
                poller = self.client.begin_analyze_document("prebuilt-receipt", document=f)
                result = poller.result()
                logger.info(f"Successfully analyzed: {image_path}")
                return result.to_dict()
        except Exception as e:
            logger.error(f"Error analyzing {image_path}: {e}")
            return None

    def analyze_folder(self, input_dir, output_dir):
        ensure_dir(output_dir)

        for filename in os.listdir(input_dir):
            if filename.lower().endswith('.png'):
                input_path = os.path.join(input_dir, filename)
                output_filename = os.path.splitext(filename)[0] + ".json"
                output_path = os.path.join(output_dir, output_filename)

                # 이미 처리된 경우 스킵
                if os.path.exists(output_path):
                    logger.info(f"Skipping already processed: {output_path}")
                    continue

                result = self.analyze_receipt(input_path)
                if result:
                    try:
                        def convert_date(obj):
                            if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
                                return obj.isoformat()
                            raise TypeError(f"Type {type(obj)} not serializable")

                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=4, default=convert_date)
                            logger.info(f"Saved result: {output_path}")

                    except Exception as e:
                        logger.error(f"Error saving result for {filename}: {e}")

if __name__ == "__main__":
    client = AzureReceiptClient()
    client.analyze_folder('./processed_images', './results/json')