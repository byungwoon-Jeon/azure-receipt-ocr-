from PIL import Image
import os

def convert_jpg_to_png(folder_path):
    for filename in os.listdir(folder_path):
        base, ext = os.path.splitext(filename)
        if ext.lower() in ['.jpg', '.jpeg']:
            jpg_path = os.path.join(folder_path, filename)
            png_path = os.path.join(folder_path, base + '.png')

            try:
                with Image.open(jpg_path) as img:
                    img.convert("RGB").save(png_path, "PNG")
                os.remove(jpg_path)  # 기존 jpg 파일 삭제 (선택)
                print(f"Converted: {filename} → {base}.png")
            except Exception as e:
                print(f"Error converting {filename}: {e}")