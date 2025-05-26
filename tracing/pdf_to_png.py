from pdf2image import convert_from_path
import os

def pdf_to_png(pdf_path, output_folder='output_images', dpi=300):
    # 출력 폴더가 없으면 생성
    os.makedirs(output_folder, exist_ok=True)

    # PDF를 이미지로 변환
    images = convert_from_path(pdf_path, dpi=dpi)

    saved_files = []

    for i, img in enumerate(images):
        output_path = os.path.join(output_folder, f'page_{i+1}.png')
        img.save(output_path, 'PNG')
        saved_files.append(output_path)

    print(f"총 {len(saved_files)}개의 페이지가 PNG로 저장되었습니다.")
    return saved_files

# 사용 예시
if __name__ == "__main__":
    pdf_path = 'example.pdf'  # 변환할 PDF 경로
    pdf_to_png(pdf_path)