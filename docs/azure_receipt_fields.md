# Azure Receipt OCR 필드 구조 문서

## 1. 요약
Azure **Prebuilt Receipt 모델**은 영수증 이미지에서 주요 정보를 추출하여 **key-value 형태**로 반환합니다. 결과는 단일 필드와 항목 리스트 (`Items`)로 구성됩니다.


## 2. 주요 필드 목록

| 필드명                  | 설명                              | 타입     |
|---------------------|---------------------------------|--------|
| `MerchantName`      | 가맹점 이름                           | String |
| `MerchantPhoneNumber` | 가맹점 전화번호                         | String |
| `MerchantAddress`   | 가맹점 주소                           | String |
| `TransactionDate`   | 거래 날짜                             | Date   |
| `TransactionTime`   | 거래 시간                             | Time   |
| `Subtotal`          | 세전 금액                             | Number |
| `Tax`               | 세금                                 | Number |
| `Tip`               | 팁 금액 (있을 경우)                     | Number |
| `Total`             | 총액                                 | Number |
| `Items`             | 구매 항목 리스트 (배열)                  | Array  |


## 3. Items 필드 구조

| 필드명        | 설명                     | 타입     |
|-------------|------------------------|--------|
| `Description` | 항목 설명 (제품명 등)         | String |
| `Quantity`   | 수량                      | Number |
| `Price`      | 단가 (개당 가격)              | Number |
| `TotalPrice` | 총액 (단가 × 수량)            | Number |


## 4. 샘플 JSON (수정 버전)

```json
{
  "documents": [
    {
      "fields": {
        "MerchantName": { "value": "미니스톱", "confidence": 0.95 },
        "TransactionDate": { "value": "2025-04-28", "confidence": 0.97 },
        "Total": { "value": 24050, "confidence": 0.99 },
        "Items": {
          "value": [
            {
              "Description": { "value": "라크프리미엄원" },
              "Quantity": { "value": 1 },
              "TotalPrice": { "value": 2500 }
            },
            {
              "Description": { "value": "우육탕큰사발" },
              "Quantity": { "value": 1 },
              "TotalPrice": { "value": 1050 }
            }
          ]
        }
      }
    }
  ]
}
```


## 5. 주의사항 (한글 영수증 특징)
- 가맹점 주소, 전화번호, 날짜 등이 **누락**되거나 **오인식**될 수 있습니다.
- `Items` 내 `Quantity`, `Price`가 빠지거나 불안정할 수 있습니다 (후처리 필요).

