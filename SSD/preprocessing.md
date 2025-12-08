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
    """
    YOLO 모델을 이용해 영수증 영역을 탐지하고, 탐지된 영역만 잘라(crop) 저장하는 함수.

    전체 역할 요약:
    1) YOLO에 PNG 이미지(png_path)를 입력하여 바운딩 박스(영수증 후보 영역)를 얻는다.
    2) YOLO 결과에서 박스 좌표(x1, y1, x2, y2)와 신뢰도(conf)를 추출하여 dets 리스트로 만든다.
       - 이미지 범위를 벗어나는 좌표는 화면 안으로 클램프(보정)한다.
       - 가로/세로가 0 이하인 박스는 무시한다.
    3) _nms_and_merge()를 통해
       - 너무 작은 박스/이상한 비율 박스 제거
       - 서로 많이 겹치거나 포함되는 박스 제거(중복 박스 정리)
       를 수행한다.
       - ATTACH_FILE인 경우 topk=1로 설정하여 최종 1개만 남기도록 한다.
       - FILE_PATH인 경우 여러 개 박스를 그대로 허용한다.
    4) 최종 박스(clean)를 기준으로 원본 이미지(original_img)를 crop하여 파일로 저장한다.
       - ATTACH_FILE: 항상 1장만 저장, 파일명은 "<base>_receipt.png"
       - FILE_PATH  : 탐지된 박스 개수만큼 저장, 파일명은 "<base>_r{번호}.png"
    5) 각 크롭된 이미지에 대해 FIID, LINE_INDEX 등 메타 정보를 포함한 딕셔너리를 results 리스트에 담아 반환한다.
       - 실패/에러 상황에서는 RESULT_CODE, RESULT_MESSAGE가 포함된 딕셔너리를 반환한다.

    파라미터 설명:
    - model (YOLO):
        학습된 YOLO 모델 객체. model(png_path, ...) 형태로 추론을 수행한다.

    - png_path (str):
        YOLO에 입력할 PNG 이미지 파일 경로.
        (전처리 단계에서 다운로드/변환 완료된 파일)

    - file_type (str):
        "ATTACH_FILE" 또는 "FILE_PATH" 중 하나.
        - ATTACH_FILE: 첨부 이미지 한 장에 영수증 한 개가 있다는 가정(최대 1개 허용)
        - FILE_PATH  : 한 장 이미지 안에 영수증 여러 개가 있을 수 있음

    - base_filename (str):
        출력 파일 이름의 기본 이름(확장자 제외).
        예) "abc_123.png" → base_filename="abc_123"

    - original_img (PIL.Image.Image):
        YOLO 결과 좌표로 crop할 때 사용할 원본 이미지 객체.

    - fiid (str), line_index (int), gubun (str), receipt_index (int | None), common_yn (int):
        DB에 넣기 위한 식별자/메타 정보.
        - fiid, line_index, gubun: 원본 레코드 식별용
        - receipt_index          : 영수증 순번(ATTACH_FILE의 경우 보통 1)
        - common_yn              : ATTACH_FILE(0) / FILE_PATH(1) 등 구분용 플래그

    - cropped_dir (str):
        잘라낸 영수증 이미지 파일을 저장할 디렉토리 경로.

    반환값:
    - list[dict]:
        각 영수증별 결과를 나타내는 딕셔너리 리스트.
        - 성공 시: {"FIID", "LINE_INDEX", "GUBUN", "RECEIPT_INDEX", "COMMON_YN", "file_path", ...}
        - 실패 시: {"FIID", "LINE_INDEX", "GUBUN", "RECEIPT_INDEX": None, "COMMON_YN", "RESULT_CODE", "RESULT_MESSAGE", ...}
    """
    logger.info("[시작] crop_receipts_with_yolo")
    results = []

    try:
        # ① YOLO 추론 수행
        #   - conf, iou 인자를 통해 최소 신뢰도/겹침 허용 정도를 조절한다.
        #   - conf  : 낮출수록 더 많은 박스가 검출(노이즈 증가 가능)
        #   - iou   : 높일수록 NMS 단계에서 박스를 덜 합침(겹쳐도 둘 다 남길 수 있음)
        #   - 필요시 in_params 등을 통해 외부 설정값으로 빼서 조정 가능.
        yolo_results = model(png_path, conf=0.4, iou=0.6)
        boxes = yolo_results[0].boxes  # 첫 번째(단일) 이미지 결과의 바운딩 박스 목록

        # YOLO가 아무 박스도 찾지 못한 경우
        if boxes is None or len(boxes) == 0:
            logger.warning("YOLO 탐지 결과 없음")
            results.append({
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "GUBUN": gubun,
                "RECEIPT_INDEX": None,
                "COMMON_YN": common_yn,
                "RESULT_CODE": "E001",
                "RESULT_MESSAGE": "YOLO 탐지 결과 없음"
            })
            logger.info("[종료] crop_receipts_with_yolo")
            return results

        # 크롭 이미지를 저장할 폴더 생성 (없으면 생성)
        os.makedirs(cropped_dir, exist_ok=True)

        # 원본 이미지 크기 (경계 체크용)
        W, H = original_img.size

        # ② YOLO 결과에서 xyxy 좌표 + conf 추출
        #    - dets = [(x1, y1, x2, y2, conf), ...] 형태로 구성
        #    - 이미지 경계를 벗어난 좌표는 0~W, 0~H 범위로 보정
        dets = []
        for b in boxes:
            # b.xyxy: tensor 형태의 [x1, y1, x2, y2]
            xyxy = b.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(float, xyxy)

            # 신뢰도(conf): YOLO가 해당 박스를 얼마나 확신하는지(0~1)
            conf = float(b.conf[0].cpu().numpy()) if getattr(b, "conf", None) is not None else 1.0

            # 이미지 범위를 벗어나는 좌표는 강제로 화면 안으로 클램프
            # (음수 좌표, W/H를 넘는 좌표 등 보호)
            x1 = max(0, min(x1, W - 1))
            x2 = max(1, min(x2, W))
            y1 = max(0, min(y1, H - 1))
            y2 = max(1, min(y2, H))

            # 보정 후에도 유효하지 않은(너비/높이가 0 이하인) 박스는 스킵
            if x2 <= x1 or y2 <= y1:
                continue

            dets.append((x1, y1, x2, y2, conf))

        # 보정 과정 이후에 남은 유효 박스가 하나도 없을 때
        if not dets:
            logger.warning("YOLO 탐지 후 유효 박스 없음")
            results.append({
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "GUBUN": gubun,
                "RECEIPT_INDEX": None,
                "COMMON_YN": common_yn,
                "RESULT_CODE": "E001",
                "RESULT_MESSAGE": "YOLO 유효 박스 없음"
            })
            logger.info("[종료] crop_receipts_with_yolo")
            return results

        # ③ 후처리(NMS + 규칙 기반 필터링) 수행
        #    - _nms_and_merge 함수에서
        #        · 너무 작은 박스 / 비정상 비율 박스 제거
        #        · 서로 많이 겹치거나(높은 IoU), 한 박스가 다른 박스를 거의 포함하는 경우 정리
        #      를 수행함.
        #    - ATTACH_FILE:
        #        영수증 1장만 있어야 하므로 topk=1로 설정 → 최종적으로 1개만 남도록 함.
        #    - FILE_PATH:
        #        한 파일에 여러 영수증이 있을 수 있으므로 topk=None으로 두어 제한 없음.
        topk = 1 if file_type == "ATTACH_FILE" else None

        clean = _nms_and_merge(
            dets,
            iou_merge_thresh=0.7,      # 두 박스 IoU가 이 이상이면 중복으로 판단하여 합친다고 봄
            contain_thresh=0.9,        # 큰 박스가 작은 박스를 이 비율 이상으로 포함하면 작은 박스를 제거
            min_area_ratio=0.03,       # 전체 이미지 면적 대비 3% 미만인 박스 제거(노이즈 제거용)
            aspect_min=0.7, aspect_max=8.0,  # 세로/가로 비가 이 범위를 벗어나면 이상한 박스로 보고 제거
            img_w=W, img_h=H,          # 면적 비율 계산용 이미지 크기
            topk=topk,                 # ATTACH_FILE이면 최종 1개만 유지, FILE_PATH면 제한 없음
            # verbose / logger_는 기본값 사용
        )

        # 후처리까지 했는데도 남은 박스가 없는 경우
        if not clean:
            logger.warning("후처리 후 박스 없음")
            results.append({
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "GUBUN": gubun,
                "RECEIPT_INDEX": None,
                "COMMON_YN": common_yn,
                "RESULT_CODE": "E003",
                "RESULT_MESSAGE": "후처리 후 박스 없음"
            })
            logger.info("[종료] crop_receipts_with_yolo")
            return results

        # ④ 후처리된 박스를 기준으로 실제 이미지 크롭 및 파일 저장
        if file_type == "ATTACH_FILE":
            # ATTACH_FILE:
            #   - 정책상 영수증 1장만 허용
            #   - NMS에서 topk=1로 강제했으므로 clean[0]만 사용
            x1, y1, x2, y2, _ = clean[0]
            cropped_img = original_img.crop((int(x1), int(y1), int(x2), int(y2)))

            # 저장 파일명: "<base_filename>_receipt.png"
            cropped_path = os.path.join(cropped_dir, f"{base_filename}_receipt.png")
            cropped_img.save(cropped_path)

            # 크롭된 파일 크기 검증(10MB 이상 등 체크) → 실패 시 예외 발생 가능
            validate_file_size(cropped_path)

            # 성공 결과 저장
            results.append({
                "FIID": fiid,
                "LINE_INDEX": line_index,
                "GUBUN": gubun,
                "RECEIPT_INDEX": receipt_index or 1,  # ATTACH_FILE은 보통 1
                "COMMON_YN": common_yn,
                "file_path": cropped_path
            })

        else:  # FILE_PATH
            # FILE_PATH:
            #   - 한 이미지에 여러 영수증(여러 박스)이 있을 수 있음
            #   - clean에 남은 박스 개수만큼 순회하며 r1, r2, ... 형식으로 저장
            for idx, b in enumerate(clean, 1):
                x1, y1, x2, y2, _ = b
                cropped_img = original_img.crop((int(x1), int(y1), int(x2), int(y2)))

                # 저장 파일명: "<base_filename>_r{idx}.png"
                cropped_path = os.path.join(cropped_dir, f"{base_filename}_r{idx}.png")
                cropped_img.save(cropped_path)

                # 크롭된 파일 크기 검증
                validate_file_size(cropped_path)

                # 각 영수증별 결과 딕셔너리 추가
                results.append({
                    "FIID": fiid,
                    "LINE_INDEX": line_index,
                    "GUBUN": gubun,
                    "RECEIPT_INDEX": idx,   # FILE_PATH에서는 1부터 시작하는 순번
                    "COMMON_YN": common_yn,
                    "file_path": cropped_path
                })

    except Exception as e:
        # 예기치 못한 모든 에러는 여기서 잡는다.
        logger.error(f"[ERROR] YOLO 크롭 오류: {e}")
        traceback.print_exc()

    logger.info("[종료] crop_receipts_with_yolo")
    return results

def _nms_and_merge(
    boxes_xyxy_conf,
    iou_merge_thresh=0.7,
    contain_thresh=0.9,
    min_area_ratio=0.03,
    aspect_min=0.7,
    aspect_max=8.0,
    img_w=None,
    img_h=None,
    topk=None,
    verbose=True,
    logger_=logger
):
    """
    YOLO 등의 Object Detection 결과(바운딩 박스 리스트)에 대해
    1단계: 너무 작은 박스 / 비정상적인 종횡비 박스를 제거하고,
    2단계: 서로 많이 겹치거나(High IoU) 한 박스가 다른 박스를 거의 완전히 포함하는 경우
          중복으로 판단하여 하나로 정리하는 후처리 함수입니다.

    [입력 형식]
    - boxes_xyxy_conf: 리스트[튜플] 형식의 박스 정보
        각 원소는 (x1, y1, x2, y2, conf) 형태입니다.
        - (x1, y1): 박스의 좌상단 좌표
        - (x2, y2): 박스의 우하단 좌표
        - conf    : 해당 박스의 신뢰도(score)

    [주요 파라미터]
    - iou_merge_thresh (float):
        두 박스의 IoU(겹치는 비율)가 이 값 이상이면
        "중복"으로 판단하여 하나만 남깁니다.
        값이 클수록 겹침에 관대(= 겹쳐도 둘 다 살려둠),
        값이 작을수록 조금만 겹쳐도 제거됩니다.

    - contain_thresh (float):
        박스 A가 박스 B를 얼마나 "포함"하는지 비율 기준입니다.
        (A와 B의 겹치는 영역 / B의 전체 영역)
        이 값 이상이면 "B가 A에 거의 완전히 포함되었다"고 보고
        B를 제거합니다.

    - min_area_ratio (float):
        박스 하나의 면적 / 전체 이미지 면적 이 이 값보다 작으면
        "너무 작은 박스(노이즈)"로 보고 제거합니다.
        예: 0.03이면 전체 이미지의 3% 미만인 박스는 제거.

    - aspect_min, aspect_max (float):
        세로/가로 비율(h / w)이 이 범위를 벗어나면
        "너무 납작하거나 너무 길쭉한 박스"로 보고 제거합니다.
        (실제 데이터에 맞게 튜닝 필요)

    - img_w, img_h (int):
        전체 이미지의 가로·세로 크기.
        min_area_ratio 계산 시 사용됩니다.
        (None이면 min_area_ratio 필터는 건너뜀)

    - topk (int | None):
        후처리된 박스 중에서 최종적으로 conf 상위 몇 개만 남길지 개수.
        - None: 개수 제한 없음
        - 정수: 해당 개수만큼만 남김
        (ATTACH_FILE 정책 등에 따라 호출부에서 설정)

    - verbose (bool):
        True이면 NMS 처리 단계별 디버그 로그를 남깁니다.

    - logger_ (logging.Logger):
        로그를 출력할 로거 객체. (외부에서 주입받아 사용)

    [출력]
    - final (list[tuple]):
        후처리된 박스 리스트.
        구조는 입력과 동일하게 (x1, y1, x2, y2, conf) 튜플 리스트입니다.
    """
    import math

    def area(b):
        """
        단일 박스의 면적 계산 함수.
        b: (x1, y1, x2, y2, conf) 형태의 튜플
        """
        return max(0, b[2] - b[0]) * max(0, b[3] - b[1])

    def iou(a, b):
        """
        두 박스 a, b 사이의 IoU(Intersection over Union)를 계산합니다.
        IoU = (겹치는 영역 넓이) / (a 면적 + b 면적 - 겹치는 영역 넓이)
        """
        # 겹치는 영역의 좌상단/우하단 좌표 계산
        ix1 = max(a[0], b[0])
        iy1 = max(a[1], b[1])
        ix2 = min(a[2], b[2])
        iy2 = min(a[3], b[3])

        # 겹치는 영역의 너비, 높이
        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)
        inter = iw * ih  # 교집합 면적

        if inter == 0:
            return 0.0

        # 합집합 = a 면적 + b 면적 - 교집합
        return inter / (area(a) + area(b) - inter + 1e-9)

    def contains(a, b):
        """
        박스 a가 박스 b를 얼마나 포함하고 있는지 비율을 계산하여,
        contain_thresh 이상이면 "a가 b를 사실상 감싸고 있다"고 판단합니다.

        비율 정의:
        (a와 b의 겹치는 영역 넓이) / (b의 전체 면적)
        """
        ix1 = max(a[0], b[0])
        iy1 = max(a[1], b[1])
        ix2 = min(a[2], b[2])
        iy2 = min(a[3], b[3])

        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)
        inter = iw * ih

        return inter / (area(b) + 1e-9) >= contain_thresh

    # 0) 우선 conf(신뢰도) 기준 내림차순 정렬
    #    → 나중에 중복 제거할 때, 더 좋은 박스를 먼저 final에 쌓기 위해
    boxes = sorted(boxes_xyxy_conf, key=lambda x: x[4], reverse=True)

    if verbose:
        logger_.debug(
            f"[NMS] 시작: {len(boxes)}개, img=({img_w}x{img_h}), "
            f"min_area_ratio={min_area_ratio}, aspect=[{aspect_min},{aspect_max}], "
            f"contain>={contain_thresh}, iou_merge>={iou_merge_thresh}"
        )

    # ----------------------------------------------------
    # 1) 너무 작은 박스 / 비정상 종횡비 박스 제거 단계
    # ----------------------------------------------------
    kept = []  # 1차 필터를 통과한 박스들
    img_area = (img_w * img_h) if (img_w and img_h) else None
    removed_small = 0      # 크기가 작아서 제거된 개수(면적 기준 포함)
    removed_aspect = 0     # 종횡비 때문에 제거된 개수

    for b in boxes:
        w = b[2] - b[0]  # 박스 너비
        h = b[3] - b[1]  # 박스 높이

        # (1) 픽셀 기준으로 너무 작은 박스 제거 (가로/세로가 5픽셀 이하인 경우)
        if w <= 5 or h <= 5:
            removed_small += 1
            continue

        # (2) 전체 이미지 대비 면적 비율이 min_area_ratio보다 작은 경우 제거
        if img_area and area(b) / img_area < min_area_ratio:
            removed_small += 1
            continue

        # (3) 세로/가로 비율(aspect ratio)이 지정 범위를 벗어나면 제거
        ar = (h / (w + 1e-9))
        if not (aspect_min <= ar <= aspect_max):
            removed_aspect += 1
            continue

        # 위 세 조건을 모두 통과한 박스만 kept에 남김
        kept.append(b)

    if verbose:
        logger_.debug(
            f"[NMS] 1단계 후: {len(kept)}개 "
            f"(작음/면적/비율 제거 {removed_small + removed_aspect}개)"
        )

    # ----------------------------------------------------
    # 2) 포함/중복(높은 IoU) 박스 정리 단계
    #    - conf가 높은 박스부터 final에 담으면서,
    #      이미 선택된 박스들과 중복되는 박스들을 걸러낸다.
    # ----------------------------------------------------
    final = []               # 최종 박스 리스트
    removed_contain_iou = 0  # 포함/IoU 조건으로 제거된 개수

    for b in kept:
        drop = False  # 이 박스를 버릴지 여부

        for f in final:
            # 이미 선택된 박스 f가 현재 박스 b를 거의 감싸거나(contains),
            # f와 b의 IoU가 iou_merge_thresh 이상이면
            # "중복"으로 판단 → b는 버림
            if contains(f, b) or iou(f, b) >= iou_merge_thresh:
                removed_contain_iou += 1
                drop = True
                break

        if not drop:
            # 어떤 final 박스와도 충분히 다르다고 판단되면 final에 추가
            final.append(b)

    if verbose:
        logger_.debug(
            f"[NMS] 2단계 후: {len(final)}개 (포함/IoU 제거 {removed_contain_iou}개)"
        )

    # ----------------------------------------------------
    # 3) top-k 적용 (선택 사항)
    #    - topk가 지정된 경우, conf 기준 상위 k개만 남긴다.
    # ----------------------------------------------------
    if topk is not None and len(final) > topk:
        # conf 기반 내림차순 정렬 후 상위 topk개만 사용
        final = sorted(final, key=lambda x: x[4], reverse=True)[:topk]
        if verbose:
            logger_.debug(f"[NMS] topk={topk} 적용 후: {len(final)}개")

    return final

========================================

함수 SDD: crop_receipts_with_yolo
========================================

[함수 이름]
crop_receipts_with_yolo

[역할 개요]
YOLO 모델을 이용해 한 장의 이미지에서 영수증 후보 영역(바운딩 박스)을 탐지한 뒤,

좌표를 이미지 범위 안으로 보정하고,

후처리(_nms_and_merge)를 통해 너무 작은 박스, 이상한 비율, 중복 박스를 제거한 후,

최종 박스를 기준으로 원본 이미지를 crop해서 파일로 저장하고,

DB에 넣기 위한 메타 정보(FIID, LINE_INDEX, GUBUN, RECEIPT_INDEX, COMMON_YN, file_path 등)를 결과 리스트로 반환한다.

ATTACH_FILE 인 경우에는 “이미지 1장 = 영수증 1개”라는 정책을 따르므로 최종 1개만 남도록 처리하고,
FILE_PATH 인 경우에는 “이미지 1장에 여러 영수증 가능”으로 처리하여 여러 장을 잘라낸다.

[함수 시그니처]
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

[입력 파라미터 설명]

model (YOLO)

학습된 YOLO 모델 객체.

model(png_path, conf=..., iou=...) 형태로 추론을 수행한다.

png_path (str)

YOLO에 입력할 PNG 이미지 파일 경로.

전처리 단계에서 다운로드 및 포맷 변환이 완료된 파일을 사용한다.

file_type (str)

"ATTACH_FILE" 또는 "FILE_PATH" 중 하나.

ATTACH_FILE:
· 첨부 이미지 한 장에 영수증 한 개가 있다는 가정.
· 최종적으로 1개의 박스만 남기도록 후처리에서 제한.

FILE_PATH:
· 한 장의 이미지 안에 여러 영수증이 있을 수 있음.
· 여러 개의 박스를 그대로 허용.

base_filename (str)

출력할 크롭 이미지 파일 이름의 베이스 이름(확장자 제외).

예: 원본 파일명이 "abc_123.png"라면 base_filename="abc_123" 형태로 들어온다고 가정.

original_img (PIL.Image.Image)

실제 crop 작업에 사용할 원본 이미지 객체.

YOLO 박스 좌표(x1, y1, x2, y2)는 이 이미지 기준으로 잘라낸다.

fiid (str)

line_index (int)

gubun (str)

원본 레코드 식별을 위한 키 값들.

이후 DB에 결과를 저장할 때 PK 또는 조건절로 사용된다.

receipt_index (int 또는 None)

영수증 순번 정보.

ATTACH_FILE의 경우 보통 1을 사용하며, 코드에서는 receipt_index 값이 없으면 1로 대체한다.

common_yn (int)

ATTACH_FILE / FILE_PATH 구분 등 플래그 용도로 사용하는 값.

cropped_dir (str)

크롭된 영수증 이미지를 저장할 디렉터리 경로.

존재하지 않으면 os.makedirs(cropped_dir, exist_ok=True)로 생성한다.

[출력 형식]

반환값: list[dict]

성공 케이스(박스 탐지 및 크롭 성공 시)
각 원소는 다음과 같은 형태의 dict:
{
"FIID": fiid,
"LINE_INDEX": line_index,
"GUBUN": gubun,
"RECEIPT_INDEX": <크롭된 영수증 순번>,
"COMMON_YN": common_yn,
"file_path": "<크롭된 이미지 파일 경로>"
}

실패 / 에러 케이스

YOLO에서 박스를 찾지 못한 경우

보정 후 유효 박스가 하나도 없는 경우

후처리 결과 박스가 모두 제거된 경우 등
다음과 같은 필드를 포함:
{
"FIID": fiid,
"LINE_INDEX": line_index,
"GUBUN": gubun,
"RECEIPT_INDEX": None,
"COMMON_YN": common_yn,
"RESULT_CODE": "E001" 또는 "E003" 등,
"RESULT_MESSAGE": "에러 설명 문자열"
}

[상세 처리 흐름]

1단계. YOLO 추론 수행

model(png_path, conf=0.4, iou=0.6) 형태로 호출하여 박스 후보를 얻는다.

conf: 최소 신뢰도 기준(낮을수록 더 많은 박스가 검출되지만 노이즈가 증가할 수 있음)

iou: YOLO 내부 NMS 기준 (겹치는 박스를 얼마나 합칠지 결정)

코드:
yolo_results = model(png_path, conf=0.4, iou=0.6)
boxes = yolo_results[0].boxes

박스가 하나도 없으면:
· RESULT_CODE = "E001"
· RESULT_MESSAGE = "YOLO 탐지 결과 없음"
형태의 dict를 results에 추가하고 함수 종료.

2단계. 좌표 보정 및 유효 박스 리스트(dets) 구성

원본 이미지 크기 W, H를 구한다. (original_img.size)

각 box에 대해 b.xyxy[0]을 사용해 (x1, y1, x2, y2)를 가져오고, conf를 추출한다.

좌표 보정(클램프):
· x1, x2는 0 ~ (W 또는 W-1) 범위로 보정
· y1, y2는 0 ~ (H 또는 H-1) 범위로 보정

보정 후 x2 <= x1 또는 y2 <= y1인 경우는 잘못된 박스로 간주하고 스킵한다.

최종적으로 dets 리스트에 (x1, y1, x2, y2, conf) 튜플을 담는다.

dets가 비어 있으면:
· RESULT_CODE = "E001"
· RESULT_MESSAGE = "YOLO 유효 박스 없음"
형태의 dict를 results에 추가하고 함수 종료.

3단계. 후처리(_nms_and_merge) 호출

ATTACH_FILE과 FILE_PATH에 따라 topk을 다르게 설정한다.
· ATTACH_FILE: topk=1 (최종 박스 1개만 허용)
· FILE_PATH : topk=None (개수 제한 없음)

코드:
topk = 1 if file_type == "ATTACH_FILE" else None

clean = _nms_and_merge(
dets,
iou_merge_thresh=0.7,
contain_thresh=0.9,
min_area_ratio=0.03,
aspect_min=0.7,
aspect_max=8.0,
img_w=W,
img_h=H,
topk=topk,
)

clean 리스트가 비어 있으면:
· RESULT_CODE = "E003"
· RESULT_MESSAGE = "후처리 후 박스 없음"
형태의 dict를 results에 추가하고 함수 종료.

4단계. 실제 이미지 크롭 및 파일 저장

(1) file_type == "ATTACH_FILE" 인 경우

clean[0] 하나만 사용한다. (이미 topk=1로 제한됨)

original_img.crop((x1, y1, x2, y2))로 영수증 영역을 잘라낸다.

파일명 규칙: "<base_filename>_receipt.png"

cropped_path = os.path.join(cropped_dir, f"{base_filename}_receipt.png")

cropped_img.save(cropped_path)

validate_file_size(cropped_path)로 파일 크기 검증 수행.

결과 dict:
{
"FIID": fiid,
"LINE_INDEX": line_index,
"GUBUN": gubun,
"RECEIPT_INDEX": receipt_index or 1,
"COMMON_YN": common_yn,
"file_path": cropped_path
}
를 results에 추가.

(2) file_type == "FILE_PATH" 인 경우

clean 리스트에 남은 모든 박스를 순회한다. (enumerate(clean, 1))

각 박스마다 original_img.crop으로 잘라낸다.

파일명 규칙: "<base_filename>_r{idx}.png"
· 예: base_filename="abc_123" 이고 idx=1이면 "abc_123_r1.png"

validate_file_size(cropped_path)로 파일 크기를 검증한다.

각 결과에 대해:
{
"FIID": fiid,
"LINE_INDEX": line_index,
"GUBUN": gubun,
"RECEIPT_INDEX": idx,
"COMMON_YN": common_yn,
"file_path": cropped_path
}
형태로 results에 추가한다.

5단계. 예외 처리

전체 로직은 try/except로 감싸져 있으며, 예기치 못한 모든 예외를 잡는다.

except에서:
· logger.error("[ERROR] YOLO 크롭 오류: {e}")로 에러 로그를 남기고,
· traceback.print_exc()로 스택 트레이스를 출력한다.

이후 logger.info("[종료] crop_receipts_with_yolo") 로그를 남기고,
· 현재까지 results에 쌓인 내용을 반환한다.

[에러 코드 정책 정리]

E001:
· YOLO 탐지 결과가 없거나, 보정 후 유효 박스가 하나도 없는 경우.
· RESULT_MESSAGE: "YOLO 탐지 결과 없음" 또는 "YOLO 유효 박스 없음"

E003:
· _nms_and_merge 후처리 과정에서 모든 박스가 제거되어 최종 박스가 없는 경우.
· RESULT_MESSAGE: "후처리 후 박스 없음"

========================================
2. 함수 SDD: _nms_and_merge

[함수 이름]
_nms_and_merge

[역할 개요]
YOLO 등 Object Detection 결과로부터 얻은 바운딩 박스 리스트에 대해,

너무 작은 박스, 비정상적인 종횡비 박스, 전체 이미지 대비 면적이 너무 작은 박스를 제거하고,

서로 많이 겹치거나(High IoU), 한 박스가 다른 박스를 거의 완전히 포함하는 경우를 중복으로 판단하여 정리하며,

필요할 경우 최종 박스를 신뢰도 상위 top-k 개로 제한하여 반환하는 후처리 함수이다.

중복 박스를 제거함으로써, 실제로 사용할 “의미 있는 영수증 영역”만 남기는 역할을 한다.

[함수 시그니처]
def nms_and_merge(
boxes_xyxy_conf,
iou_merge_thresh=0.7,
contain_thresh=0.9,
min_area_ratio=0.03,
aspect_min=0.7,
aspect_max=8.0,
img_w=None,
img_h=None,
topk=None,
verbose=True,
logger=logger
):

[입력 파라미터 설명]

boxes_xyxy_conf (list[tuple])

각 원소: (x1, y1, x2, y2, conf)

x1, y1: 좌상단 좌표

x2, y2: 우하단 좌표

conf : 해당 박스의 신뢰도(score)

iou_merge_thresh (float)

두 박스 사이의 IoU(Intersection over Union)가 이 값 이상이면
“중복”으로 보고 하나의 박스만 남긴다.

값이 클수록 겹치는 것에 관대해져서 여러 박스가 같이 살아남을 수 있고,
값이 작을수록 조금만 겹쳐도 제거된다.

contain_thresh (float)

박스 A와 B가 있을 때,
(A와 B의 겹치는 영역 면적) / (B 박스 면적) 비율이 이 값 이상이면,
“B가 A에 거의 완전히 포함되었다”고 판단한다.

이 경우 B를 제거하는 식으로 중복을 정리한다.

min_area_ratio (float)

박스 면적 / 전체 이미지 면적이 이 값보다 작은 경우,
“너무 작은 노이즈 박스”라고 판단하여 제거한다.

예: 0.03이면 전체 이미지의 3% 미만인 박스는 제거.

aspect_min, aspect_max (float)

세로/가로 비율(h / w)이 이 범위를 벗어나면
“너무 납작하거나, 너무 길쭉한 비정상적인 비율”로 판단하여 제거.

실제 영수증 가로/세로 비율에 맞게 값 조정 가능.

img_w, img_h (int 또는 None)

전체 이미지의 가로, 세로 길이.

min_area_ratio 계산에 사용되며, 둘 중 하나라도 None이면 면적 비율 필터는 사용하지 않는다.

topk (int 또는 None)

최종적으로 남길 박스 수를 제한하는 값.

None: 개수 제한 없음.

정수: conf 기준 상위 topk개만 남긴다. (예: ATTACH_FILE 정책에서 1개만 필요할 때)

verbose (bool)

True인 경우 처리 단계별로 디버그 로그를 남긴다.

logger_ (logging.Logger)

로그 출력을 담당하는 로거 객체.

[출력 형식]

반환값: list[tuple]

후처리된 박스 리스트.

각 원소는 입력과 동일한 구조: (x1, y1, x2, y2, conf)

[내부 헬퍼 함수 설명]

area(b)

입력: b = (x1, y1, x2, y2, conf)

기능: 박스의 면적을 계산한다.
· max(0, x2 - x1) * max(0, y2 - y1)

iou(a, b)

두 박스 a, b의 IoU(Intersection over Union)를 계산한다.

IoU = (겹치는 영역 면적) / (a 면적 + b 면적 - 겹치는 영역 면적)

값이 0에 가까우면 거의 겹치지 않는 것이고, 1에 가까우면 거의 동일한 박스이다.

contains(a, b)

“a가 b를 얼마나 포함하는가”를 계산한다.

(a와 b의 겹치는 면적) / (b의 전체 면적) >= contain_thresh 이면,
“a가 b를 거의 감싸고 있다”고 판단한다.

이 경우 b는 제거 대상이 된다.

[상세 처리 흐름]

0단계. 신뢰도(conf) 기준 정렬

boxes_xyxy_conf를 conf 기준 내림차순으로 정렬한다.
· boxes = sorted(boxes_xyxy_conf, key=lambda x: x[4], reverse=True)

목적:
· 나중에 중복 제거를 할 때, 더 신뢰도가 높은 박스부터 final에 쌓기 위해서이다.
· 이렇게 하면, 중복 관계일 때 “좋은 박스”를 우선적으로 남기게 된다.

1단계. 작은 박스 및 비정상 종횡비 박스 제거

kept 리스트를 만들어 1차 필터링을 통과한 박스를 보관한다.

img_area = img_w * img_h (둘 다 존재할 때만 계산)

각 박스 b = (x1, y1, x2, y2, conf)에 대해:
· w = x2 - x1
· h = y2 - y1

(1) 픽셀 기준 최소 크기 필터

w <= 5 또는 h <= 5 이면 "너무 작은 박스"로 보고 제거한다.

(2) 전체 이미지 대비 면적 비율 필터

img_area가 존재하고, area(b) / img_area < min_area_ratio 이면 제거한다.

즉, 전체 이미지의 min_area_ratio(예: 3%) 미만인 박스는 노이즈로 간주.

(3) 세로/가로 비율 필터

aspect ratio ar = h / (w + 1e-9)

ar가 aspect_min ~ aspect_max 범위를 벗어나면 제거한다.

예: aspect_min=0.7, aspect_max=8.0인 경우,
· 지나치게 가로로 긴(너무 납작한) 박스
· 지나치게 세로로 긴(너무 길쭉한) 박스를 제거한다.

· 위 조건에 모두 걸리지 않은 박스만 kept에 추가한다.

결과적으로 kept에는 “크기와 비율 면에서 어느 정도 정상적인 박스”만 남게 된다.

2단계. 포함/중복(IoU) 박스 정리

final 리스트를 만들어 최종 박스를 담는다.

kept를 정렬된 순서대로 순회하면서, 각 박스를 b라고 할 때:
· drop = False로 시작한다.
· 이미 final에 들어간 박스 f들과 하나씩 비교한다.

비교 시:
(1) contains(f, b)가 True인 경우

f가 b를 거의 완전히 감싸고 있으므로,
“b는 f에 포함된 중복 박스”라고 판단하여 drop=True 설정.

(2) 또는, iou(f, b) >= iou_merge_thresh 인 경우

f와 b가 상당 부분 겹치는 중복이라고 보고 drop=True 설정.

· 위 두 조건 중 하나라도 만족하면, b는 final에 추가하지 않고 폐기한다.
· 어떤 final 박스와도 이런 조건을 만족하지 않는다면, b를 final에 추가한다.

이 과정을 통해 같은 영수증을 나타내는 중복 박스들이 제거되고,
서로 충분히 다른(서로 다른 영수증으로 보이는) 박스들만 남게 된다.

3단계. top-k 적용

topk가 None이 아니고, len(final) > topk 인 경우에만 적용한다.

final을 다시 conf 기준 내림차순 정렬한 뒤 상위 topk개만 남긴다.
· 예: ATTACH_FILE의 경우 topk=1을 넣으면 가장 신뢰도 높은 1개만 남는다.

topk가 None이라면 개수 제한을 하지 않고 final 전체를 반환한다.

[튜닝 포인트 요약]

iou_merge_thresh
· 값이 낮을수록 조금만 겹쳐도 중복으로 보고 제거된다.
· 값이 높을수록 겹쳐도 같이 남을 수 있다.

contain_thresh
· 두 박스 중 하나가 다른 하나를 “얼마나 많이 포함하고 있어야” 중복으로 볼지 결정한다.

min_area_ratio
· 전체 이미지 대비 너무 작은 객체를 제거하는 기준.
· 영수증 자체가 작게 찍힌 이미지가 많은 경우 이 값을 너무 크게 잡으면 실제 영수증도 제거될 수 있으므로 주의.

aspect_min, aspect_max
· 실제 영수증의 일반적인 세로/가로 비율에 맞게 조정하는 것이 좋다.
· 종이 영수증이 너무 들쭉날쭉할 경우, 범위를 넓게 잡는 것이 안전하다.

topk
· ATTACH_FILE처럼 “파일당 1개만 허용”하는 정책에 사용.
· FILE_PATH처럼 “여러 개도 허용”인 경우 None으로 둔다.