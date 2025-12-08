[ 원본 이미지 (ATTACH_FILE / FILE_PATH) ]
        ↓
download → PNG 변환 → 회전 등 기본 전처리
        ↓
load original_img (PIL.Image)
        ↓
YOLO 추론 실행 (conf / iou 적용)
        ↓
YOLO 결과 박스 → 좌표 보정 & 유효 박스 필터링
        ↓
_nms_and_merge 로 작은 박스 제거 + 중복 박스 정리
        ↓
ATTACH_FILE → 최종 1개 crop
FILE_PATH   → 여러 개 crop
        ↓
crop 이미지 저장 (*.png)
(FIID, LINE_INDEX, GUBUN, RECEIPT_INDEX, COMMON_YN 포함)
        ↓
results 리스트 반환



[ cropped receipt PNG ]
        ↓
open file (rb)
        ↓
Azure Form Recognizer 호출 (prebuilt-receipt)
        ↓
poller.result() → AnalyzeResult
        ↓
to_dict() 변환
        ↓
"<base>.ocr.json" 저장
        ↓
result_dict 반환
(실패 시 AZURE_ERR JSON 생성)



[ OCR JSON (*.ocr.json) ]
        ↓
load JSON from file
        ↓
extract OCR fields → summary 생성
  - COUNTRY, MERCHANT, DATE/TIME, TOTAL, TAX 등
  - FIID / LINE_INDEX / RECEIPT_INDEX 포함
        ↓
Items 배열 파싱 → items 리스트 생성
  - ITEM_INDEX, ITEM_NAME, QTY, PRICE, TOTAL_PRICE 등
        ↓
{"summary": summary, "items": items} 구조 생성
        ↓
"{FIID}_{LINE_INDEX}_{RECEIPT_INDEX}_post.json" 저장
        ↓
정상: post.json 경로 반환
오류: POST_ERR 요약 + 빈 items → fail.json 저장


