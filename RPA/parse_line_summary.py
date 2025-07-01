import json
from datetime import datetime
from pathlib import Path
import re

def parse_line_summary(json_path: str, file_info_dict: dict) -> dict:
    """
    JSON 결과 파일을 파싱하여 라인 요약 테이블에 들어갈 데이터를 구성한다.

    Args:
        json_path (str): JSON 파일 경로
        file_info_dict (dict): {
            "FIID": str,
            "LINE_INDEX": int,
            "ATTACH_FILE": str,
            "COMMON_YN": str,  # 'Y' or 'N'
            "FILENAME": str    # 이미지 파일명 (ex: sample_3.jpg)
        }

    Returns:
        dict: DB insert를 위한 dict 구조
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        document = data.get("analyzeResult", {}).get("documents", [{}])[0]
        fields = document.get("fields", {})
        lines = document.get("lines", [])

        def get_value(key, subkey):
            return fields.get(key, {}).get(subkey)

        fiid = file_info_dict["FIID"]
        line_index = file_info_dict["LINE_INDEX"]
        common_yn = file_info_dict["COMMON_YN"]
        attach_file = file_info_dict["ATTACH_FILE"]

        # receipt_index 추출 (_n 형식에서 n을 파싱)
        match = re.search(r"_(\d+)\.jpg", file_info_dict["FILENAME"])
        receipt_index = int(match.group(1)) if match else 0

        # 기본 정보 추출
        country = get_value("CountryRegion", "valueCountryRegion")
        receipt_type = get_value("ReceiptType", "valueString")
        merchant_name = get_value("MerchantName", "valueString")
        merchant_phone = get_value("MerchantPhoneNumber", "valuePhoneNumber")
        transaction_date = get_value("TransactionDate", "valueDate")
        transaction_time = get_value("TransactionTime", "valueTime")
        total_amount = get_value("Total", "valueCurrency") or {}
        total_tax = get_value("TotalTax", "valueCurrency") or {}
        total_amount_val = total_amount.get("amount")
        tax_amount_val = total_tax.get("amount")
        sumtotal_amount = (
            round(total_amount_val - tax_amount_val, 2)
            if total_amount_val is not None and tax_amount_val is not None
            else None
        )

        # 사업자번호 / 배송지 주소 추출 (라인에서)
        biz_no = None
        delivery_addr = None
        for line in lines:
            content = line.get("content", "")
            if not biz_no:
                match = re.search(r"\d{3}-\d{2}-\d{5}", content)
                if match:
                    biz_no = match.group()
            if not delivery_addr and "address" in content.lower():
                delivery_addr = content

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "FIID": fiid,
            "LINE_INDEX": line_index,
            "RECEIPT_INDEX": receipt_index,
            "COMMON_YN": common_yn,
            "ATTACH_FILE": attach_file,
            "COUNTRY": country,
            "RECEIPT_TYPE": receipt_type,
            "MERCHANT_NAME": merchant_name,
            "MERCHANT_PHONE_NO": merchant_phone,
            "DELIVERY_ADDR": delivery_addr,
            "TRANSACTION_DATE": transaction_date,
            "TRANSACTION_TIME": transaction_time,
            "TOTAL_AMOUNT": total_amount_val,
            "SUMTOTAL_AMOUNT": sumtotal_amount,
            "TAX_AMOUNT": tax_amount_val,
            "BIZ_NO": biz_no,
            "RESULT_CODE": 200,
            "RESULT_MESSAGE": "",
            "CREATE_DATE": now_str,
            "UPDATE_DATE": now_str,
        }

    except Exception as e:
        return {
            "FIID": file_info_dict.get("FIID"),
            "LINE_INDEX": file_info_dict.get("LINE_INDEX"),
            "RECEIPT_INDEX": 0,
            "COMMON_YN": file_info_dict.get("COMMON_YN"),
            "ATTACH_FILE": file_info_dict.get("ATTACH_FILE"),
            "COUNTRY": None,
            "RECEIPT_TYPE": None,
            "MERCHANT_NAME": None,
            "MERCHANT_PHONE_NO": None,
            "DELIVERY_ADDR": None,
            "TRANSACTION_DATE": None,
            "TRANSACTION_TIME": None,
            "TOTAL_AMOUNT": None,
            "SUMTOTAL_AMOUNT": None,
            "TAX_AMOUNT": None,
            "BIZ_NO": None,
            "RESULT_CODE": 500,
            "RESULT_MESSAGE": str(e),
            "CREATE_DATE": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "UPDATE_DATE": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

# 두 샘플 JSON 파일 테스트용 정보
sample_input_1 = {
    "FIID": "FIID001",
    "LINE_INDEX": 1,
    "ATTACH_FILE": "https://example.com/receipt1.jpg",
    "COMMON_YN": "N",
    "FILENAME": "receipt-app-like_3.jpg"
}

sample_input_2 = {
    "FIID": "FIID002",
    "LINE_INDEX": 2,
    "ATTACH_FILE": "https://example.com/receipt2.jpg",
    "COMMON_YN": "Y",
    "FILENAME": "receipt-with-tips_2.jpg"
}

# 실행
result1 = parse_line_summary("/mnt/data/receipt-app-like.png (1).json", sample_input_1)
result2 = parse_line_summary("/mnt/data/receipt-with-tips.jpg.json", sample_input_2)

import pandas as pd
import ace_tools as tools; tools.display_dataframe_to_user(name="Parsed Line Summary", dataframe=pd.DataFrame([result1, result2]))
