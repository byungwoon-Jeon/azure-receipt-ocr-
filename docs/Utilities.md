# Python Utilities for On-Premises Workflow

이 문서는 온프렘 환경에서 자주 사용되는 Python 유틸리티 함수들을 정리한 자료입니다. 파일/폴더 관리, 시스템 관리, 데이터 처리, 시간 처리 등 다양한 작업에 필요한 함수와 코드 예제를 포함합니다.

---

## 1. 파일 및 디렉토리 관리 (os, shutil)

```python
import os
import shutil

# 디렉토리 생성 (없으면)
os.makedirs('./results/json', exist_ok=True)

# 파일 리스트 가져오기 (특정 확장자)
files = [f for f in os.listdir('./input') if f.endswith('.json')]

# 경로를 절대 경로로 변환
abs_path = os.path.abspath('./input/file.json')

# 파일 복사
shutil.copy('source.txt', 'dest.txt')

# 파일/디렉토리 이동
shutil.move('source_folder', 'dest_folder')

# 디렉토리 삭제
shutil.rmtree('old_results')
```

---

## 2. 시스템 및 프로세스 관리 (subprocess, multiprocessing)

```python
import subprocess
import multiprocessing

# 외부 명령어 실행
result = subprocess.run(['ls', '-l'], capture_output=True, text=True)
print(result.stdout)

# 외부 명령어 출력만 얻기
output = subprocess.check_output(['echo', 'Hello World'], text=True)
print(output)

# CPU 코어 수 얻기
cpu_count = multiprocessing.cpu_count()

# 활성화된 자식 프로세스 목록
active_children = multiprocessing.active_children()
```

---

## 3. 시간 및 날짜 처리 (time, datetime)

```python
import time
import datetime

# 현재 시간 (초 단위)
current_time = time.time()

# 일정 시간 대기
time.sleep(2)  # 2초 대기

# 현재 날짜와 시간
now = datetime.datetime.now()

# 날짜 포맷팅
formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
```

---

## 4. JSON 처리 (json)

```python
import json

# JSON 읽기
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# JSON 쓰기
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
```

---

## 5. CSV 처리 (csv)

```python
import csv

# CSV 파일 읽기
with open('data.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row)

# CSV 파일 쓰기
with open('output.csv', 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['name', 'age']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow({'name': 'Alice', 'age': 30})
```

---

## 6. 데이터 처리 (sorted, enumerate, zip, map, filter)

```python
# sorted
nums = [5, 2, 9]
print(sorted(nums))  # [2, 5, 9]

# enumerate
for idx, val in enumerate(['a', 'b', 'c']):
    print(idx, val)

# zip
names = ['Alice', 'Bob']
ages = [30, 25]
for name, age in zip(names, ages):
    print(name, age)

# map
nums = ['1', '2', '3']
nums_int = list(map(int, nums))

# filter
nums = [1, 2, 3, 4]
even_nums = list(filter(lambda x: x % 2 == 0, nums))
```

---

## 7. 에러 처리 및 디버깅 (try-except, logging)

```python
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# 예외 처리
try:
    1 / 0
except ZeroDivisionError as e:
    logging.error(f"Error occurred: {e}")
```

---

## 8. 환경변수 불러오기 (dotenv)

```python
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경변수 읽기
api_key = os.getenv('API_KEY')
```

---

이 문서는 온프렘 환경에서 빠르게 작업을 시작할 수 있도록 자주 쓰이는 유틸리티 함수들을 모아놓은 자료입니다.

