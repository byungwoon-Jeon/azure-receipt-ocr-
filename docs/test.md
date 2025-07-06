ocr_receipt_summary
| 컬럼명                     | 타입          | 설명                |
| ----------------------- | ----------- | ----------------- |
| `fiid`                  | VARCHAR(64) | 양식 문서 고유 ID       |
| `attachment_file`       | TEXT        | 첨부파일명 (영수증 이미지 등) |
| `merchant_name`         | TEXT        | 상점명               |
| `merchant_phone_number` | VARCHAR(32) | 상점 전화번호           |
| `transaction_date`      | DATE        | 거래 날짜             |
| `transaction_time`      | TIME        | 거래 시간             |
| `total_amount`          | NUMERIC     | 총 거래 금액           |
| `subtotal_amount`       | NUMERIC     | 세금 전 금액           |
| `tax_amount`            | NUMERIC     | 세금 금액             |
| `error_message`         | TEXT        | 오류 메시지 (실패 시)     |
Primary Key: (fiid, attachment_file)


ocr_receipt_items
| 컬럼명               | 타입          | 설명          |
| ----------------- | ----------- | ----------- |
| `fiid`            | VARCHAR(64) | 양식 문서 고유 ID |
| `attachment_file` | TEXT        | 첨부파일명       |
| `item_index`      | INT         | 항목 순번       |
| `description`     | TEXT        | 항목 설명       |
| `quantity`        | NUMERIC     | 수량          |
| `price`           | NUMERIC     | 단가          |
| `total_price`     | NUMERIC     | 항목 총액       |
Primary Key: (fiid, attachment_file, item_index)
Foreign Key: (fiid, attachment_file) → ocr_receipt_summary


ocr_receipt_summary_unmapped
| 컬럼명                     | 타입          | 설명                |
| ----------------------- | ----------- | ----------------- |
| `fiid`                  | VARCHAR(64) | 양식 문서 고유 ID       |
| `attachment_file`       | TEXT        | 첨부파일명 (영수증 이미지 등) |
| `merchant_name`         | TEXT        | 상점명               |
| `merchant_phone_number` | VARCHAR(32) | 상점 전화번호           |
| `transaction_date`      | DATE        | 거래 날짜             |
| `transaction_time`      | TIME        | 거래 시간             |
| `total_amount`          | NUMERIC     | 총 거래 금액           |
| `subtotal_amount`       | NUMERIC     | 세금 전 금액           |
| `tax_amount`            | NUMERIC     | 세금 금액             |
| `error_message`         | TEXT        | 오류 메시지 (실패 시)     |
Primary Key: (fiid, attachment_file)


ocr_receipt_items_unmapped
| 컬럼명               | 타입          | 설명          |
| ----------------- | ----------- | ----------- |
| `fiid`            | VARCHAR(64) | 양식 문서 고유 ID |
| `attachment_file` | TEXT        | 첨부파일명       |
| `item_index`      | INT         | 항목 순번       |
| `description`     | TEXT        | 항목 설명       |
| `quantity`        | NUMERIC     | 수량          |
| `price`           | NUMERIC     | 단가          |
| `total_price`     | NUMERIC     | 항목 총액       |
Primary Key: (fiid, attachment_file, item_index)
Foreign Key: (fiid, attachment_file) → ocr_receipt_summary