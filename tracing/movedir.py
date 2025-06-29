import os
import shutil
import random
from pathlib import Path

# 파라미터 설정
base_dir = Path("3rd_train")
train_images_dir = base_dir / "train" / "images"
train_labels_dir = base_dir / "train" / "labels"

valid_images_dir = base_dir / "valid" / "images"
valid_labels_dir = base_dir / "valid" / "labels"

# 유효한 확장자
valid_exts = [".jpg", ".jpeg", ".png"]

# valid 비율
valid_ratio = 0.2  # 20%를 valid로 분리

# 유효한 이미지 목록 수집
image_files = [f for f in train_images_dir.iterdir() if f.suffix.lower() in valid_exts]
random.shuffle(image_files)

# 분할
num_valid = int(len(image_files) * valid_ratio)
valid_images = image_files[:num_valid]
train_images = image_files[num_valid:]

# 디렉토리 생성
for d in [valid_images_dir, valid_labels_dir]:
    d.mkdir(parents=True, exist_ok=True)

# valid로 파일 이동
for img_path in valid_images:
    label_path = train_labels_dir / (img_path.stem + ".txt")

    # 이미지와 라벨 복사
    shutil.move(str(img_path), str(valid_images_dir / img_path.name))
    if label_path.exists():
        shutil.move(str(label_path), str(valid_labels_dir / label_path.name))

print(f"✅ 전체 {len(image_files)}개 중 {num_valid}개를 valid로 분리 완료.")