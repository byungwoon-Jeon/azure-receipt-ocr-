import os

def rename_all_to_png(folder_path):
    for filename in os.listdir(folder_path):
        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            new_name = base + '.png'
            src = os.path.join(folder_path, filename)
            dst = os.path.join(folder_path, new_name)
            os.rename(src, dst)
            print(f"Renamed: {filename} → {new_name}")

# 사용 예시
folder_path = "C:/your/folder/path"  # <- 대상 폴더 경로로 수정
rename_all_to_png(folder_path)