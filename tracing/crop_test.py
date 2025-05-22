from ultralytics import YOLO
from PIL import Image
import os

# 모델 로드
model = YOLO("best.pt")

# 입력 이미지 디렉토리 (val set)
input_dir = "./dataset/images/val"
output_dir = "./val_crops"
os.makedirs(output_dir, exist_ok=True)

# 이미지 파일 순회
for filename in os.listdir(input_dir):
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue

    image_path = os.path.join(input_dir, filename)
    results = model(image_path)[0]

    image = Image.open(image_path)
    basename = os.path.splitext(filename)[0]

    for i, box in enumerate(results.boxes.xyxy):
        x1, y1, x2, y2 = map(int, box.tolist())
        cropped = image.crop((x1, y1, x2, y2))
        cropped.save(os.path.join(output_dir, f"{basename}_crop{i+1}.jpg"))

print("✅ 크롭 완료!")