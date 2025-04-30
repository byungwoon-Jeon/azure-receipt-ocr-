import os
import csv
import pandas as pd
from utils import setup_logger, ensure_dir, load_json

# 로깅 설정
logger = setup_logger('postprocessing')

# 룩업 테이블 로드
def load_lookup_table(path):
    """
    상호명 정규화를 위한 룩업 테이블 로드

    Args:
        path (str): CSV 파일 경로 (컬럼: original_name, normalized_name)
        
    Returns:
        dict: original_name -> normalized_name 매핑 딕셔너리
    """
    try:
        df = pd.read_csv(path)
        lookup_dict = dict(zip(df['original_name'], df['normalized_name']))
        logger.info(f"[성공] 룩업 테이블 로드 완료: {path}")
        return lookup_dict
    except Exception as e:
        logger.error(f"[에러] 룩업 테이블 로드 실패 : {e}")
        return {}
    
# JSON 데이터에서 필드 추출
def extract_fields(json_data):
    """
    OCR 결과 JSON에서 주요 필드 추출

    Args:
        json_data (dict): OCR 결과
        
    Returns:
    tuple: (merchant_name, total_price)
    """
    try:
        fields = json_data.get('documents', [])[0].get('fields', {})
        merchant = fields.get('MerchantName', {}).get('value', '') or fields.get('MerchantName',{}).get('content', '')
        total = fields.get('Total', {}).get('value', '')
        return merchant, total
    except Exception as e:
        logger.warning(f"[경고] 필드 추출 실패: {e}")
        return '', ''
    
# 폴더 전체 결과 후처리
def process_folder(input_dir, output_csv, lookup_table):
    """
    OCR JSON 결과들을 정제하고 CSV로 저장

    Args:
        input_dir (str): JSON 파일 폴더
        output_csv (str): 결과 CSV 저장 경로
        lookup_table (dict): 상호명 정규화 룩업 테이블
    """
    try:
        output_dir = os.path.dirname(output_csv) or '.'
        ensure_dir(output_dir, logger)
        rows = []
        
        for filename in os.listdir(input_dir):
            if filename.endswith('.json'):
                json_path = os.path.join(input_dir, filename)
                data = load_json(json_path, logger)
                
                if data is None:
                    logger.warning(f"[스킵] JSON 로드 실패: {filename}")
                    continue
                
                merchant, total = extract_fields(data)
                normalized_merchant = lookup_table.get(merchant, merchant)
                if merchant != normalized_merchant:
                    logger.info(f"[정규화] '{merchant}' -> '{normalized_merchant}'")
                else:
                    logger.warning(f"[경고] 정규화 미일치 : {merchant}")
                
                rows.append({
                    'filename' : filename,
                    'merchant' : merchant,
                    'normalized_merchant' : normalized_merchant,
                    'total':total   
                })
                logger.info(f"[처리] {filename}->상호: {merchant}, 금액: {total}")
        # CSV 저장
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['filename', 'merchant', 'normalized_merchant', 'total']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"[완료] CSV 저장 완료: {output_csv}")
        
    except Exception as e:
        logger.exception(f"[예외] 폴더 후처리 중 오류 발생: {e}")

# =============================================
# 단독 실행 진입점
# =============================================
if __name__ == "__main__":
    lookup = load_lookup_table('./lookup_table.csv')
    process_folder('./results/json', './results/csv/final_output.csv', lookup)