import os
from collections import Counter

# 루트 폴더 (각 하위 폴더들이 들어있는 상위 폴더)
root_dir = "./your/root/folder"  # 예: "C:/data/receipt"

# 확장자 수집
ext_counter = Counter()

for folder_name in os.listdir(root_dir):
    folder_path = os.path.join(root_dir, folder_name)
    if not os.path.isdir(folder_path):
        continue

    for file_name in os.listdir(folder_path):
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        ext_counter[ext] += 1

# 결과 출력
print("전체 확장자 분포:")
for ext, count in ext_counter.items():
    print(f"{ext or '[없음]'}: {count}개")