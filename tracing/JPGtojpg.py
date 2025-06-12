import os

def rename_extensions_to_lowercase(folder_path):
    for filename in os.listdir(folder_path):
        base, ext = os.path.splitext(filename)
        # 확장자가 있고 대문자인 경우만 처리
        if ext and ext != ext.lower():
            new_name = base + ext.lower()
            src = os.path.join(folder_path, filename)
            dst = os.path.join(folder_path, new_name)
            os.rename(src, dst)
            print(f"Renamed: {filename} -> {new_name}")

# 사용 예시
folder_path = "C:/your/folder/path"  # <- 여기에 대상 폴더 경로 입력
rename_extensions_to_lowercase(folder_path)