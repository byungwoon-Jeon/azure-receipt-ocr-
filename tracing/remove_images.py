import os
import shutil
from pathlib import Path

# 경로 설정
base_dir = Path("3rd_train")
images_dir = base_dir / "train" / "images"
labels_dir = base_dir / "train" / "labels"
invalid_dir = Path("3rd_train_invalid")

# 저장 경로 생성
invalid_dir.mkdir(parents=True, exist_ok=True)

# 이미지 확장자 목록
valid_extensions = [".jpg", ".jpeg", ".png"]

# 이미지 파일 순회
for image_file in images_dir.iterdir():
    if image_file.suffix.lower() not in valid_extensions:
        continue  # 이미지 파일만 처리

    # 라벨 파일 경로 (확장자만 .txt로 바꿈)
    label_file = labels_dir / (image_file.stem + ".txt")

    if not label_file.exists():
        # 라벨이 없는 경우 → invalid 폴더로 이미지 이동
        print(f"[!] 라벨 없음: {image_file.name} → {invalid_dir}")
        shutil.move(str(image_file), str(invalid_dir / image_file.name))