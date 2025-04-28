# Azure Receipt OCR 파이프라인 문서

## 1. 파이프라인 전체 흐름

```
1. 이미지 전처리 (preprocessing.py)
   - 리사이즈 + 패딩 + 그레이스케일 (OpenCV)

2. Azure OCR 호출 (azure_client.py)
   - Prebuilt Receipt 모델 (SDK 사용)
   - 결과를 JSON으로 저장

3. OCR 결과 후처리 (postprocessing.py)
   - 필요한 필드 추출 (가맹점명, 총액)
   - 룩업 테이블 적용 (가맹점명 정제)
   - CSV로 저장

4. 로깅 (logger_utils.py)
   - 각 단계별 로그 기록 (모듈별 로그 파일)
```

---

## 2. 각 단계 상세

### 1) 이미지 전처리 (`preprocessing.py`)
- **대상 폴더**: `./input_images` → `./processed_images`
- **작업 내용**:
  - 이미지를 **1024x1024** 크기로 **비율 유지 리사이즈**.
  - 부족한 부분은 **검정색 패딩** 추가.
  - **그레이스케일 변환**.
  - 확장자 상관없이 **PNG로 저장**.

---

### 2) Azure OCR 호출 (`azure_client.py`)
- **대상 폴더**: `./processed_images` → `./results/json`
- **작업 내용**:
  - Azure Form Recognizer **Prebuilt Receipt 모델** 사용.
  - **Azure SDK** (`azure-ai-formrecognizer`) 사용.
  - 결과를 **JSON 형태**로 저장 (날짜 포맷은 ISO).

---

### 3) OCR 결과 후처리 (`postprocessing.py`)
- **대상 폴더**: `./results/json` → `./results/csv/final_output.csv`
- **작업 내용**:
  - JSON에서 **가맹점명 (`MerchantName`)**과 **총액 (`Total`)** 추출.
  - **룩업 테이블** (`lookup_table.csv`)로 가맹점명 **정제**.
  - 결과를 CSV로 저장:
    - `filename`, `merchant`, `normalized_merchant`, `total`

---

### 4) 로깅 (`logger_utils.py`)
- 각 단계별로 **모듈별 로그 파일** 생성:
  - `logs/preprocessing_날짜시간.log`
  - `logs/azure_client_날짜시간.log`
  - `logs/postprocessing_날짜시간.log`

- **로그 내용**:
  - 작업 시작/완료
  - 오류 발생 시 상세 기록

