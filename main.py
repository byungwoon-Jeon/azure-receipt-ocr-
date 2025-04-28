from preprocessing import preprocess_folder
from azure_client import AzureReceiptClient
from postprocessing import load_lookup_table, process_folder
from logger_utils import setup_logger
import os

# 로그 설정
logger = setup_logger('main')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Created directory: {path}")

def main():
    try:
        logger.info("=== Step 1: Preprocessing Start ===")
        preprocess_folder('./input_images', './processed_images')
        logger.info("=== Step 1: Preprocessing Done ===")

        logger.info("=== Step 2: Azure Receipt Analysis Start ===")
        client = AzureReceiptClient()
        client.analyze_folder('./processed_images', './results/json')
        logger.info("=== Step 2: Azure Receipt Analysis Done ===")

        logger.info("=== Step 3: Postprocessing Start ===")
        lookup_table = load_lookup_table('./lookup_table.csv')
        process_folder('./results/json', './results/csv/final_output.csv', lookup_table)
        logger.info("=== Step 3: Postprocessing Done ===")

    except Exception as e:
        logger.error(f"Error in main process: {e}")

if __name__ == "__main__":
    main()