import os
import json
import csv
import pandas as pd
from logger_utils import setup_logger

# 로그 설정
logger = setup_logger('postprocessing')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Created directory: {path}")

def load_lookup_table(path):
    """룩업 테이블 로드"""
    try:
        df = pd.read_csv(path)
        lookup_dict = dict(zip(df['original_name'], df['normalized_name']))
        logger.info(f"Loaded lookup table: {path}")
        return lookup_dict
    except Exception as e:
        logger.error(f"Error loading lookup table: {e}")
        return {}

def extract_fields(json_data):
    """JSON에서 필요한 필드 추출"""
    try:
        fields = json_data.get('documents', [])[0]['fields']
        merchant = fields.get('MerchantName', {}).get('value', '')
        total = fields.get('Total', {}).get('value', '')
        return merchant, total
    except Exception as e:
        logger.error(f"Error extracting fields: {e}")
        return '', ''

def process_folder(input_dir, output_csv, lookup_table):
    ensure_dir(os.path.dirname(output_csv))

    rows = []
    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            input_path = os.path.join(input_dir, filename)
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                merchant, total = extract_fields(data)

                # 룩업 테이블 적용
                normalized_merchant = lookup_table.get(merchant, merchant)

                rows.append({
                    'filename': filename,
                    'merchant': merchant,
                    'normalized_merchant': normalized_merchant,
                    'total': total
                })

                logger.info(f"Processed {filename}")

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

    # CSV 저장
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'merchant', 'normalized_merchant', 'total']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        logger.info(f"Saved CSV: {output_csv}")

if __name__ == "__main__":
    lookup_table = load_lookup_table('./lookup_table.csv')
    process_folder('./results/json', './results/csv/final_output.csv', lookup_table)