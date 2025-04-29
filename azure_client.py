import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from utils import setup_logger, ensure_dir, save_json
from datetime import datetime

# .env 파일 로드
load_dotenv()

# 설정값
ENDPOINT = os.getenv("AZURE_FROM_RECOGNIZER_ENDPOINT")
KEY = os.getenv("AZURE_FROM_RECOGNIZER_KEY")
LOG_DIR = './logs'

# 로거 설정
logger = setup_logger('azure_client', log_dir=LOG_DIR)

# Azure 클라이언트 클래스
class AzureReceiptClient:
    def __init__(self):
        """Azure Form Recognizer 클라이언트 초기회"""
        try:
            self.client = DocumentAnalysisClient(
                endpoint=ENDPOINT,
                credential=AzureKeyCredential(KEY)
            )
            logger.info("[성공] Azure 클라이언트 초기화 완료")
        except Exception as e:
            logger.exception(f"[실패] Azure 클라이언트 초기화 실패: {e}")
            raise e
    
    def analyze_receipt(self, image_path):
        """
        단일 영수증 이미지 분석

        Args:
            image_path (str): 이미지 파일 경로
        
        Returns:
            dict: 분석 결과 JSON
        """
        try:
            with open(image_path, "rb") as f:
                poller = self.client.begin_analyze_document("prebuilt-receipt", document=f)
                result = poller.result()
                logger.info(f"[성공] 분석 완료 : {image_path}")
                return result.to_dict()
        except Exception as e:
            logger.error(f"[실패] 분석 실패: {image_path} - {e}")
            return None
    
    def analyze_folder(self, input_dir, output_dir):
        """
        폴더 내 모든 이미지 분석 후 결과 저장

        Args:
            input_dir (str): 전처리 된 이미지 폴더
            output_dir (str): 분석 결과 저장 폴더
        """
        try:
            ensure_dir(output_dir, logger)
            
            files = os.listdir(input_dir)
            for filename in files:
                if filename.lower().endswith('.png'):
                    input_path = os.path.join(input_dir, filename)
                    output_filename = os.path.splitext(filename)[0] + ".json"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    if os.path.exists(output_path):
                        logger.info(f"[스킵] 이미 처리된 파일 : {filename}")
                        continue
                    
                    result = self.analyze_receipt(input_path)
                    
                    if result:
                        save_json(result, output_path, logger)
                    else:
                        logger.warning(f"[경고] 결과 없음 : {filename}")
            
            logger.info(f"[완료] 폴더 분석 및 저장 완료 : {input_dir} -> {output_dir}")
        
        except Exception as e:
            logger.exception(f"[예외] 폴더 분석 중 오류 발생: {e}")
            
# =============================================
# 메인 진입점
# =============================================
if __name__ == "__main__":
    client = AzureReceiptClient()
    client.analyze_folder('./processed_images', './results/json')