import os
from collections import Counter

# 루트 폴더 경로
root_dir = "./your/root/folder"  # 예: "./data"

# 폴더별 결과 저장
folder_results = {}

# 각 서브폴더에 대해 순회
for folder_name in sorted(os.listdir(root_dir)):
    folder_path = os.path.join(root_dir, folder_name)
    if not os.path.isdir(folder_path):
        continue

    # 현재 폴더 내 확장자 수집
    ext_counter = Counter()
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            ext_counter[ext] += 1

    folder_results[folder_name] = ext_counter

# 결과 출력
for folder, stats in folder_results.items():
    print(f"\n[{folder}]")
    for ext, count in stats.items():
        print(f"  {ext or '[없음]'}: {count}개")