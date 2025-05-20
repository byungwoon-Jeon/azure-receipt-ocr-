import os
from collections import Counter

# 조사할 폴더 경로 하나만 지정
folder_path = "./your/folder/path"  # 예: "./data/해외출장증빙0001-1000(1)"

# 확장자 통계 수집
raw_exts = Counter()
normalized_exts = Counter()

for file in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file)
    if os.path.isfile(file_path):
        raw_ext = os.path.splitext(file)[1]       # 원본 확장자 (대소문자 구분)
        norm_ext = raw_ext.lower()                # 소문자 통일

        raw_exts[raw_ext] += 1
        normalized_exts[norm_ext] += 1

# 출력
print(f"\n[폴더: {os.path.basename(folder_path)}]")
print("▶ 원래 확장자 분포:")
for ext, count in raw_exts.items():
    print(f"  {ext or '[없음]'}: {count}개")

print("▶ 소문자 통일시 확장자 분포:")
for ext, count in normalized_exts.items():
    print(f"  {ext or '[없음]'}: {count}개")