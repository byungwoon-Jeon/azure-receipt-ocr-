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