# Azure Receipt OCR Pipeline

## 📚 Overview
이 프로젝트는 **Azure Receipt Prebuilt 모델**을 활용하여 영수증 이미지를 OCR 분석하고, 결과를 CSV 파일로 저장하는 **전체 파이프라인**입니다.

1. **이미지 전처리**: 리사이즈 + 패딩 + 그레이스케일
2. **Azure OCR 호출**: 영수증 텍스트 분석 (Prebuilt Receipt 모델)
3. **후처리**: 룩업 테이블을 적용하여 상호명을 정규화하고 CSV로 저장

---

## 🔠 Directory Structure

```
.
├── input_images/           # 원본 이미지 저장 폴더
├── processed_images/       # 전체리된 이미지 저장 폴더
├── results/
│   ├── json/               # Azure 분석 결과 (JSON)
│   └── csv/                # 후처리 결과 (CSV)
├── logs/                   # 로그 파일 저장
├── lookup_table.csv        # 상호명 정규화용 루칩 테이블
├── preprocessing.py        # 이미지 전체리 코드
├── azure_client.py         # Azure Receipt 호출 코드
├── postprocessing.py       # 후처리 (JSON → CSV)
├── main.py                 # 전체 파이프라이네 실행
📌 logger_utils.py         # 공통 로그 설정
```

---

## 🛠️ Tech Stack

- Python 3.x
- OpenCV (Image Preprocessing)
- Azure Form Recognizer SDK (OCR)
- Pandas (CSV Processing)
- dotenv (Environment Variable Management)
- Python logging (Log Management)

---

## 🔧 Installation

```bash
git clone <repo-url>
cd <repo-directory>
python -m venv venv
source venv/bin/activate   # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

**requirements.txt**:
```
azure-ai-formrecognizer
python-dotenv
opencv-python
pandas
```

---

## 🔄 Usage

**1. 전체 파이프라이네 실행**
```bash
python main.py
```

**2. 개별 모듈 실행**
```bash
python preprocessing.py
python azure_client.py
python postprocessing.py
```

---

## 📖 Sample Output

- **Processed Image**:
  - 리사이즈 + 패딩된 이미지 (`processed_images/` 폴더)
- **JSON Result**:
  ```json
  {
      "documents": [
          {
              "fields": {
                  "MerchantName": {"value": "스타벅스코리아"},
                  "Total": {"value": 5500},
                  "TransactionDate": {"value": "2025-04-28"}
              }
          }
      ]
  }
  ```
- **CSV Output**:
  | filename           | merchant        | normalized_merchant | total |
  |--------------------|-----------------|----------------------|-------|
  | receipt1.json      | 스타벅스코리아 | 스타벅스        | 5500  |

---

## 🔗 References

- [Azure Form Recognizer Documentation](https://learn.microsoft.com/en-us/azure/ai-services/form-recognizer/)
- [OpenCV Documentation](https://docs.opencv.org/)

