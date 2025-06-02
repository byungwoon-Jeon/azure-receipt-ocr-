from PIL import Image
import os

def preprocess_image(input_path, output_path, target_dpi=(300, 300), min_size=50, max_size=10000):
    try:
        img = Image.open(input_path).convert("RGB")
        width, height = img.size

        # 리사이징 비율 결정
        scale = 1.0
        if max(width, height) > max_size:
            scale = max_size / max(width, height)
        elif min(width, height) < min_size:
            scale = min_size / min(width, height)

        if scale != 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.LANCZOS)

        # PNG로 저장 (DPI 적용)
        img.save(output_path, dpi=target_dpi, format="PNG")
        print(f"✅ Processed: {input_path}")
    except Exception as e:
        print(f"❌ Error processing {input_path}: {e}")

def preprocess_folder_all_images(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    supported_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".jfif", ".pjpeg", ".pjp")
    
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(supported_extensions):
            input_path = os.path.join(input_dir, filename)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{base_name}_processed.png")
            preprocess_image(input_path, output_path)

# 예시 사용법 (경로는 직접 설정 필요)
input_folder = "your_input_folder_path"      # 예: "./input_images"
output_folder = "your_output_folder_path"    # 예: "./output_images"
preprocess_folder_all_images(input_folder, output_folder)