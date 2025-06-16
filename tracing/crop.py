from ultralytics import YOLO
from PIL import Image

model = YOLO("best.pt")
results = model("image.jpg")

boxes = results[0].boxes

if boxes is None or len(boxes) == 0:
    print("디텍션 없음 → 원본 그대로 사용")
else:
    for box in boxes:
        coords = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
        x1, y1, x2, y2 = map(int, coords)
        img = Image.open("image.jpg")
        cropped = img.crop((x1, y1, x2, y2))
        cropped.save("cropped.jpg")