from ultralytics import YOLO
from PIL import Image

model = YOLO("best.pt")
results = model("image.jpg")

img = Image.open("image.jpg")
boxes = results[0].boxes

# 디텍션 없거나 박스 비어있을 때 → 원본 유지
if boxes is None or boxes.xyxy is None or len(boxes) == 0 or boxes.xyxy.shape[0] == 0:
    print("디텍션 없음 → 원본 그대로 사용")
else:
    for box in boxes:
        if box.xyxy is None or box.xyxy.shape[0] == 0:
            continue  # 개별 박스가 비어 있을 경우 무시

        coords = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, coords)
        cropped = img.crop((x1, y1, x2, y2))
        cropped.save("cropped.jpg")  # 원한다면 파일명 다르게 저장해도 됨