import os
import requests
import logging
import traceback
from urllib.parse import urlparse
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger("PRE_PRE_PROCESS")


def download_file_from_url(url: str, save_dir: str, is_file_path: bool = False) -> str:
    if is_file_path and not url.lower().startswith("http"):
        url = "http://apv.skhynix.com" + url
    if "@" in url:
        url = url.split("@")[0]
    os.makedirs(save_dir, exist_ok=True)
    filename = os.path.basename(urlparse(url).path)
    save_path = os.path.join(save_dir, filename)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)
    return save_path


def convert_to_png(input_path: str, save_dir: str) -> str:
    os.makedirs(save_dir, exist_ok=True)
    filename = os.path.splitext(os.path.basename(input_path))[0] + ".png"
    save_path = os.path.join(save_dir, filename)
    with Image.open(input_path) as img:
        img.convert("RGB").save(save_path, "PNG")
    return save_path


def crop_receipts_with_yolo(
    model: YOLO,
    png_path: str,
    file_type: str,
    base_filename: str,
    original_img: Image.Image,
    fiid: str,
    line_index: int,
    gubun: str,
    receipt_index: int or None,
    common_yn: int,
    cropped_dir: str
) -> list:
    results = []
    yolo_results = model(png_path)
    boxes = yolo_results[0].boxes

    if boxes is None or len(boxes) == 0:
        results.append({
            "FIID": fiid, "LINE_INDEX": line_index, "GUBUN": gubun,
            "RECEIPT_INDEX": None, "COMMON_YN": common_yn,
            "RESULT_CODE": "E001",
            "RESULT_MESSAGE": "YOLO 탐지 결과 없음"
        })
        return results

    if file_type == "ATTACH_FILE":
        if len(boxes) > 1:
            results.append({
                "FIID": fiid, "LINE_INDEX": line_index, "GUBUN": gubun,
                "RECEIPT_INDEX": None, "COMMON_YN": common_yn,
                "RESULT_CODE": "E002",
                "RESULT_MESSAGE": f"YOLO 결과 {len(boxes)}개 발견 (ATTACH_FILE는 1개만 가능)"
            })
            return results

        box_coords = boxes[0].xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, box_coords)
        cropped_img = original_img.crop((x1, y1, x2, y2))
        cropped_path = os.path.join(cropped_dir, f"{base_filename}.png")
        cropped_img.save(cropped_path)

        results.append({
            "FIID": fiid,
            "LINE_INDEX": line_index,
            "GUBUN": gubun,
            "RECEIPT_INDEX": receipt_index if receipt_index is not None else 1,
            "COMMON_YN": common_yn,
            "file_path": cropped_path
        })

    elif file_type == "FILE_PATH":
        for idx, box in enumerate(boxes, start=1):
            coords = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, coords)
            cropped_img = original_img.crop((x1, y1, x2, y2))
            cropped_path = os.path.join(cropped_dir, f"{base_filename}_{idx}.png")
            cropped_img.save(cropped_path)

            results.append({
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "GUBUN": gubun,
                "RECEIPT_INDEX": idx,
                "COMMON_YN": common_yn,
                "file_path": cropped_path
            })

    return results


def run_pre_pre_process(in_params: dict, db_record: dict) -> list:
    try:
        for key in ["output_dir", "preprocessed_dir", "cropped_dir", "yolo_model_path"]:
            assert key in in_params, f"[ERROR] '{key}' is required in in_params."
        output_dir = in_params["output_dir"]
        preproc_dir = in_params["preprocessed_dir"]
        cropped_dir = in_params["cropped_dir"]
        model_path = in_params["yolo_model_path"]

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(preproc_dir, exist_ok=True)
        os.makedirs(cropped_dir, exist_ok=True)

        fiid = db_record.get("FIID")
        line_index = db_record.get("LINE_INDEX")
        gubun = db_record.get("GUBUN")
        attach_url = db_record.get("ATTACH_FILE")
        file_url = db_record.get("FILE_PATH")

        if not attach_url and not file_url:
            raise ValueError("ATTACH_FILE와 FILE_PATH가 모두 없음 - 처리 불가")

        results = []
        model = YOLO(model_path)

        for file_type, url in [("ATTACH_FILE", attach_url), ("FILE_PATH", file_url)]:
            if not url:
                logger.info(f"{file_type} URL 없음 → 스킵")
                continue
            try:
                orig_path = download_file_from_url(url, output_dir, is_file_path=(file_type == "FILE_PATH"))
                logger.info(f"[{file_type}] 다운로드 성공: {orig_path}")

                png_path = convert_to_png(orig_path, preproc_dir)
                logger.info(f"[{file_type}] PNG 변환 완료: {png_path}")

                receipt_index = 1 if (file_type == "ATTACH_FILE" and file_url) else None
                common_yn = 0 if file_type == "ATTACH_FILE" else 1

                original_img = Image.open(png_path)
                base_filename = os.path.splitext(os.path.basename(png_path))[0]

                cropped_results = crop_receipts_with_yolo(
                    model=model,
                    png_path=png_path,
                    file_type=file_type,
                    base_filename=base_filename,
                    original_img=original_img,
                    fiid=fiid,
                    line_index=line_index,
                    gubun=gubun,
                    receipt_index=receipt_index,
                    common_yn=common_yn,
                    cropped_dir=cropped_dir
                )

                results.extend(cropped_results)

            except Exception as e:
                logger.error(f"[{file_type}] 처리 실패: {url} → {e}")
                continue

        if not results:
            raise ValueError("이미지 전처리 및 YOLO 과정에서 결과를 얻지 못했습니다.")
        return results

    except Exception as e:
        logger.error(f"[FATAL] 전처리 단계 실패: {traceback.format_exc()}")
        return []

if __name__ == "__main__":
    from pprint import pprint

    # ✅ in_params 설정
    in_params = {
        "output_dir": "./test_output",           # 다운로드된 원본 저장 경로
        "preprocessed_dir": "./test_preproc",    # PNG 변환 이미지 저장 경로
        "cropped_dir": "./test_cropped",         # YOLO 크롭 이미지 저장 경로
        "yolo_model_path": "./yolo/best.pt"      # YOLO 모델 경로 (.pt 파일)
    }

    # ✅ db_record 입력 샘플 (ATTACH_FILE만 있는 경우)
    db_record = {
        "FIID": "TEST001",
        "LINE_INDEX": 1,
        "GUBUN": "Y",
        "ATTACH_FILE": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Brandon_Sanderson_signing.jpg/640px-Brandon_Sanderson_signing.jpg",  # 테스트용 이미지
        "FILE_PATH": None
    }

    print("🚀 run_pre_pre_process() 테스트 시작")
    result = run_pre_pre_process(in_params, db_record)

    print("\n📄 결과 리스트:")
    pprint(result)

    # 결과 이미지 경로 확인
    print("\n🖼 크롭된 이미지 파일들:")
    for r in result:
        if "file_path" in r:
            print("✔", r["file_path"])
        else:
            print("❌ 오류:", r)
