from ultralytics import YOLO
from PIL import Image
import os

model = YOLO("best.pt")
image_dir = "input_images"  # 처리할 이미지 폴더
output_dir = "cropped_outputs"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(image_dir):
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        continue

    image_path = os.path.join(image_dir, filename)
    img = Image.open(image_path)

    results = model(image_path)
    boxes = results[0].boxes

    # 박스 없음 → 원본 저장
    if boxes is None or boxes.xyxy is None or len(boxes) == 0 or boxes.xyxy.shape[0] == 0:
        print(f"[{filename}] 디텍션 없음 → 원본 저장")
        img.save(os.path.join(output_dir, filename))
        continue

    for i, box in enumerate(boxes):
        if box.xyxy is None or box.xyxy.shape[0] == 0:
            continue  # 개별 박스 비었으면 무시

        coords = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, coords)

        cropped = img.crop((x1, y1, x2, y2))
        cropped_filename = f"{os.path.splitext(filename)[0]}_crop{i+1}.png"
        cropped.save(os.path.join(output_dir, cropped_filename))