import os
from collections import defaultdict, Counter

# 분석할 루트 폴더 경로
root_dir = "./your/root/folder"  # 예: "C:/data/receipt"

# 지원할 이미지 확장자
valid_exts = [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"]

# 결과 저장
folder_stats = defaultdict(Counter)

# 폴더별로 순회
for folder_name in sorted(os.listdir(root_dir)):
    folder_path = os.path.join(root_dir, folder_name)
    if not os.path.isdir(folder_path):
        continue

    for file in os.listdir(folder_path):
        ext = os.path.splitext(file)[1].lower()
        if ext in valid_exts:
            folder_stats[folder_name]["total"] += 1
            folder_stats[folder_name][ext] += 1

# 출력
for folder, stats in folder_stats.items():
    print(f"\n[{folder}]")
    print(f"  총 이미지 수: {stats['total']}")
    for ext in valid_exts:
        if stats[ext]:
            print(f"    {ext}: {stats[ext]}장")