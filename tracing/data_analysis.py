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
            
            
            import os
from collections import Counter

# 루트 폴더 경로 (여러 폴더가 들어있는 최상위 디렉토리)
root_dir = "./your/root/path"  # 예: "./data"

# 전체 확장자 카운터
total_ext_counter = Counter()

# 폴더 순회
for folder_name in os.listdir(root_dir):
    folder_path = os.path.join(root_dir, folder_name)
    if not os.path.isdir(folder_path):
        continue

    # 각 폴더 내 파일 순회
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_name)[1].lower()
            total_ext_counter[ext] += 1

# 출력
print("전체 확장자 분포:")
total = sum(total_ext_counter.values())
print(f"총 파일 수: {total}")
for ext, count in total_ext_counter.items():
    print(f"{ext or '[없음]'}: {count}개")