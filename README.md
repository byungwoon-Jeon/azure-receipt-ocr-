# 🧞 Azure Receipt OCR Pipeline

## 📚 Overview
이 프로젝트는 **Azure Form Recognizer Prebuilt Receipt 모델**을 활용하여  
영수즘 이미지를 OCR 분석하고, 전처리/후처리를 거쳐 CSV로 저장하는 **전체 자동화 파이프라인**입니다.

> ✔ 이미지 전처리 → ✔ OCR 분석 → ✔ 정제 후 CSV 저장  
> 실전 환경을 고려한 **uc6b4영팀 인수 가능한 구조 + 로깅 + 예외처리 + 유틸화**를 포함합니다.

---

## 🔧 Directory Structure

```
.
├── input_images/           # 원본 이미지
├── processed_images/       # 전처리된 이미지
├── results/
│   ├── json/               # Azure OCR 결과 (JSON)
│   └── csv/                # 후처리 CSV 결과
├── logs/                   # 로그 파일
├── lookup_table.csv        # 상호명 정규화용 루칩 테이블
├── utils.py                # 유틸 함수 모음 (로게러, 디렉토리 생성, JSON 저장 등)
├── preprocessing.py        # 이미지 전처리
├── azure_client.py         # Azure OCR 클라이언트
├── postprocessing.py       # OCR 결과 후처리 (정규화 + CSV 저장)
└── run_pipeline.py         # 전체 파이프라인 실행 스크립트
```

---

## ⚙️ Tech Stack

- **Python 3.10+**
- `opencv-python`: 이미지 전처리
- `azure-ai-formrecognizer`: Azure OCR API
- `pandas`: 후처리 & CSV 생성
- `python-dotenv`: 환경변수 관리
- `logging`: 운영용 로그 기록

---

## 📦 Installation

```bash
git clone https://github.com/byungwoon-Jeon/azure-receipt-ocr.git
cd azure-receipt-ocr
python -m venv venv
venv\Scripts\activate             # Windows
# source venv/bin/activate        # Mac/Linux
pip install -r requirements.txt
```

### requirements.txt
```
azure-ai-formrecognizer
python-dotenv
opencv-python
pandas
```

---

## 🚀 Usage

### 전체 파이프라인 실행
```bash
python run_pipeline.py
```

### 개별 단계 실행
```bash
python preprocessing.py          # 이미지 전처리
python azure_client.py           # OCR 실행
python postprocessing.py         # CSV 생성
```

---

## 📌 Sample Output

### ✅ Processed Image
→ `processed_images/` 내 전처리된 `.png` 이미지

### ✅ OCR JSON Result
```json
{
  "documents": [
    {
      "fields": {
        "MerchantName": { "value": "스타벅스코리아" },
        "Total": { "value": 5500 }
      }
    }
  ]
}
```

### ✅ Final CSV Output
| filename      | merchant        | normalized_merchant | total |
|---------------|-----------------|----------------------|-------|
| receipt1.json | 스타벅스코리아 | 스타벅스             | 5500  |

---

## 🔗 References

- [Azure Form Recognizer Docs](https://learn.microsoft.com/en-us/azure/ai-services/form-recognizer/)
- [OpenCV Docs](https://docs.opencv.org/)

---

## 🤛 Author

Byungwoon Jeon  
📧 quddnsrnt@naver.com  
🔗 [GitHub: byungwoon-Jeon](https://github.com/byungwoon-Jeon)

> 본 프로젝트는 실전 업무 기반의 OCR 파이프라인 설계 및 리파트링 실습을 목적으로 제작되었습니다.

