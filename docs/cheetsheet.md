# Python Cheatsheet for On-Premises OCR Workflow

## 1. os (파일/폴더 처리)

```python
import os

# 폴더 존재 확인 및 생성
path = './results/json'
os.makedirs(path, exist_ok=True)

# 파일 경로 합치기
file_path = os.path.join(path, 'result.json')
```

---

## 2. json (JSON 읽기/쓰기)

```python
import json

# JSON 파일 읽기
with open('result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# JSON 파일 쓰기
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
```

---

## 3. csv (CSV 쓰기)

```python
import csv

# CSV 파일 쓰기 (DictWriter)
data = [
    {'filename': 'file1.json', 'merchant': '스타벅스', 'total': 5000},
    {'filename': 'file2.json', 'merchant': '미니스톱', 'total': 3000}
]

with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['filename', 'merchant', 'total']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
```

---

## 4. pandas (데이터 가공)

```python
import pandas as pd

# CSV 읽기
lookup = pd.read_csv('lookup_table.csv')

# 데이터프레임 생성
ocr_data = pd.DataFrame({
    'merchant': ['스타벅스', '미니스톱'],
    'total': [5000, 3000]
})

# 룩업테이블 병합
merged = pd.merge(ocr_data, lookup, left_on='merchant', right_on='original_name', how='left')
```

---

## 5. OpenCV (이미지 전처리)

```python
import cv2

# 이미지 열기
img = cv2.imread('input.jpg')

# 그레이스케일 변환
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 리사이즈 (비율 유지)
h, w = gray.shape
scale = min(1024 / h, 1024 / w)
resized = cv2.resize(gray, (int(w * scale), int(h * scale)))

# 패딩 추가
padded = cv2.copyMakeBorder(
    resized,
    top=50, bottom=50, left=50, right=50,
    borderType=cv2.BORDER_CONSTANT, value=0
)

# 저장
cv2.imwrite('output.png', padded)
```

---

## 6. requests (REST API 호출)

```python
import requests

# GET 요청
response = requests.get('https://api.example.com/data')
if response.status_code == 200:
    print(response.json())

# POST 요청 (파일 업로드)
with open('image.png', 'rb') as f:
    headers = {'Ocp-Apim-Subscription-Key': 'your_key'}
    response = requests.post('https://api.example.com/ocr', headers=headers, data=f)
    print(response.json())
```

---

## 7. dotenv (환경변수 불러오기)

```python
from dotenv import load_dotenv
import os

# .env 파일 불러오기
load_dotenv()

# 환경변수 읽기
endpoint = os.getenv('AZURE_FORM_RECOGNIZER_ENDPOINT')
key = os.getenv('AZURE_FORM_RECOGNIZER_KEY')
```

---

## 8. datetime (날짜 포맷 변환)

```python
import datetime
import json

# 날짜 → ISO 포맷
now = datetime.datetime.now().isoformat()

# JSON 저장 시 날짜 포맷 변환 함수
def convert_date(obj):
    if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# JSON 저장 예시
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump({'date': datetime.datetime.now()}, f, default=convert_date)
```

---

## 9. Azure SDK (Prebuilt Receipt OCR 호출)

```python
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

# 이미지 분석
with open('receipt.png', 'rb') as f:
    poller = client.begin_analyze_document('prebuilt-receipt', document=f)
    result = poller.result()
    print(result.to_dict())
```

