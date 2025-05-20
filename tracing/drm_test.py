import fitz  # PyMuPDF
import os

pdf_path = "./your_file.pdf"

try:
    doc = fitz.open(pdf_path)
    if doc.is_encrypted:
        print("PDF는 암호화(Encrypted)되어 있습니다.")
    else:
        print("PDF는 열 수 있습니다.")
except Exception as e:
    print("PDF 열기 실패:", e)
    
import zipfile

docx_path = "./your_file.docx"

try:
    with zipfile.ZipFile(docx_path, 'r') as z:
        z.testzip()
    print("DOCX 접근 가능 (DRM 없음)")
except Exception as e:
    print("DOCX 접근 실패 (DRM 가능성 있음):", e)

import zipfile
import os

pptx_path = "./your_file.pptx"

try:
    with zipfile.ZipFile(pptx_path, 'r') as z:
        # 이미지가 있는 폴더만 추출 시도
        media_files = [f for f in z.namelist() if f.startswith("ppt/media/")]
        if media_files:
            print("PPTX 접근 가능, DRM 없음. 이미지 수:", len(media_files))
        else:
            print("PPTX는 열리지만 이미지가 없거나 비어 있음.")
except Exception as e:
    print("PPTX 접근 실패 (DRM 가능성 있음):", e)


