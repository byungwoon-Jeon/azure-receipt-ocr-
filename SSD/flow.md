ㅋㅋ 이제 감 잡았다.
아주 심플하게, 네가 캡쳐한 것처럼 “한눈에 쫘악” 보이게 각각 만들어볼게.
그냥 통째로 복붙해서 써도 돼.

⸻

[1] 전처리 + YOLO 크롭 워크플로우

[ 원본 이미지(ATTACH_FILE / FILE_PATH) ]
↓
download / PNG 변환 / 회전 등 기본 전처리
↓
load original_img (PIL.Image)
↓
run YOLO model (png_path, conf, iou)
↓
extract boxes → 좌표 클램프 & 유효 박스만 필터
↓
_nms_and_merge 로 작은 박스 / 중복 박스 정리
↓
ATTACH_FILE → 최종 1개 박스만 선택
FILE_PATH   → 남은 박스 모두 사용
↓
각 박스별로 crop & save PNG
(FIID, LINE_INDEX, GUBUN, RECEIPT_INDEX, COMMON_YN, file_path)
↓
results 리스트 반환

⸻

[2] Doc Processing (Azure OCR) 워크플로우

[ cropped receipt PNG ]
↓
open file in binary (rb)
↓
DocumentAnalysisClient(prebuilt-receipt) 호출
↓
poller.result() → AnalyzeResult
↓
to_dict() → result_dict
↓
“.ocr.json” 으로 저장
↓
result_dict 반환 (또는 AZURE_ERR 에러 dict)

⸻

[3] Post-processing 워크플로우

[ OCR JSON (.ocr.json) ]
↓
load JSON from file
↓
extract fields → summary용 주요 필드 매핑
(FIID, LINE_INDEX, RECEIPT_INDEX, 금액, 일자, 상호명 등)
↓
Items 배열 파싱 → items 리스트 생성
(ITEM_INDEX, ITEM_NAME, QTY, PRICE, TOTAL_PRICE, CONTENTS 등)
↓
{“summary”: summary, “items”: items} 구조로 합치기
↓
“{FIID}{LINE_INDEX}{RECEIPT_INDEX}post.json” 저장
↓
output JSON path 반환
(실패 시 POST_ERR 요약 + 빈 items 로 fail.json 저장)

⸻

[4] DB Master (insert_postprocessed_result) 워크플로우

[ postprocessing JSON ]
↓
load JSON from file
↓
extract summary fields & items
↓
INSERT INTO RPA_CCR_LINE_SUMM (summary)
↓
INSERT INTO RPA_CCR_LINE_ITEMS (items)
(N rows per receipt)
↓
COMMIT & DONE

이렇게 네 개를 각각 블럭으로 쓰면 SDD에서 “전처리 / Doc / Post / DB마스터” 섹션에 그대로 박기 딱 좋을 거야.