import os
from PIL import Image

def convert_images_to_pdf(base_dir, output_dir_name="pdf_outputs"):
    image_extensions = ('.png', '.jpg', '.jpeg')

    for root, _, files in os.walk(base_dir):
        images = [f for f in files if f.lower().endswith(image_extensions)]
        if not images:
            continue

        # 출력 폴더 생성
        output_dir = os.path.join(root, output_dir_name)
        os.makedirs(output_dir, exist_ok=True)

        for img_file in images:
            img_path = os.path.join(root, img_file)
            try:
                img = Image.open(img_path).convert('RGB')
                pdf_filename = os.path.splitext(img_file)[0] + '.pdf'
                pdf_path = os.path.join(output_dir, pdf_filename)
                img.save(pdf_path, 'PDF')
                print(f"[✔] {img_path} → {pdf_path}")
            except Exception as e:
                print(f"[✘] 실패: {img_path} → {e}")

if __name__ == "__main__":
    # 이 부분을 원하는 상위 폴더 경로로 바꿔줘
    input_folder = r"D:\your\image\folder\here"
    convert_images_to_pdf(input_folder)