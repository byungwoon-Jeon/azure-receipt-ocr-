# --- 어댑터: 회사 스레드 유틸용 (_adapter_execute_worker) ---
def _adapter_execute_worker(params: dict) -> dict:
    """
    idp_utils.run_in_multi_thread용 어댑터.
    입력: {"idp_item": dict, "duser_input": dict}
    출력: execute_worker의 반환 dict
    """
    return execute_worker(params["idp_item"], params["duser_input"])

#
# --- execute: 아이템 기반 병렬 처리 ---
def execute(duser_input: dict) -> str:
    logger.info("[시작] extractor.execute (아이템 기반)")

    # 1) 워킹 경로 병합 + 환경 셋업 (기존 로직 유지)
    try:
        wps = idp_setup_env.initialize_working_paths(script_path.parent)
        duser_input = {**duser_input, **wps}
    except Exception:
        logger.exception("[WARN] working paths 초기화 실패 - 계속 진행")

    vr = validate_required_fields(duser_input)
    if vr["has_error"]:
        ret = {
            "callback_url": None, "req_no": None, "cmd_id": None,
            "has_error": True, "error_message": vr["error_message"], "error_fields": vr["error_fields"],
            "idp_items": []
        }
        logger.warning(f"입력값 검증 실패: {vr['error_message']}")
        return json.dumps(ret, ensure_ascii=False, indent=2)

    duser_input = das_process_setup(duser_input)

    # 2) DB에서 대상 레코드 조회 (원본 유지)
    try:
        data_records = query_data_by_date(duser_input)
    except Exception as e:
        logger.exception("[FATAL] DB 조회 실패")
        ret = {
            "callback_url": None, "req_no": None, "cmd_id": None,
            "has_error": True, "error_message": f"DB 조회 실패: {e}", "error_fields": None,
            "idp_items": []
        }
        return json.dumps(ret, ensure_ascii=False, indent=2)

    if not data_records:
        ret = {
            "callback_url": None, "req_no": None, "cmd_id": None,
            "has_error": False, "error_message": None, "error_fields": None,
            "idp_items": []
        }
        logger.info("📭 처리할 데이터 없음")
        return json.dumps(ret, ensure_ascii=False, indent=2)

    # 3) (멀티스레드) 전처리 끝난 아이템 생성
    #    NOTE: generate_idp_items() 안에서 run_pre_process를 병렬로 돌려 OCR 대상 아이템을 만들어온다는 전제
    try:
        from pre_processing import generate_idp_items  # 네가 만든 함수
    except Exception:
        # 모듈 경로가 다르면 여기 import만 맞춰줘
        from pre_pre_process import generate_idp_items  # 예비

    idp_items = generate_idp_items(duser_input, data_records)
    if not idp_items:
        ret = {
            "callback_url": None, "req_no": None, "cmd_id": None,
            "has_error": False, "error_message": None, "error_fields": None,
            "idp_items": []
        }
        logger.info("📭 생성된 OCR 대상 아이템이 없습니다.")
        return json.dumps(ret, ensure_ascii=False, indent=2)

    # 4) (멀티스레드) 아이템 단위 워커 실행: OCR → 후처리 → DB
    func_params_list = [
        {"idp_item": idp_item, "duser_input": duser_input}
        for idp_item in idp_items
    ]

    results = idp_utils.run_in_multi_thread(
        func=_adapter_execute_worker,
        func_params_list=func_params_list,
    )

    # 5) 결과 집계 후 반환
    ret = {
        "callback_url": None, "req_no": None, "cmd_id": None,
        "has_error": any(r.get("has_error") for r in results),
        "error_message": None, "error_fields": None,
        "idp_items": results
    }
    logger.info("✅ 전체 파이프라인 완료 (아이템 기반)")
    return json.dumps(ret, ensure_ascii=False, indent=2)
    
    
    # --- execute_worker: (전처리 제외) OCR → 후처리 → DB ---
def execute_worker(idp_item: dict, duser_input: dict) -> dict:
    """
    입력: generate_idp_items()가 만든 '아이템' (전처리 완료 상태)
      필수 필드 예:
        - FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, GUBUN
        - file_path (OCR 대상 경로)
        - RESULT_CODE, RESULT_MESSAGE (전처리 결과 코드/메시지; 선택)
    출력: 처리 결과를 포함한 idp_item (has_error, error_message 갱신 등)
    """
    fiid = idp_item.get("FIID")
    line_idx = idp_item.get("LINE_INDEX")
    rcp_idx = idp_item.get("RECEIPT_INDEX")
    logger.info(f"[시작] execute_worker item={fiid}-{line_idx}-{rcp_idx}")

    # (옵션) 실행 이력 시작 기록이 있다면 여기서 호출
    # _write_history_start(idp_item, duser_input)

    try:
        # 0) 전처리 단계 실패 아이템 가드 (있다면 곧바로 실패 요약 생성)
        pre_code = str(idp_item.get("RESULT_CODE", "200"))
        if pre_code != "200":
            msg = idp_item.get("RESULT_MESSAGE") or "전처리 실패"
            logger.warning(f"[SKIP] 전처리 실패 아이템: {fiid}-{line_idx}-{rcp_idx} / {msg}")
            try:
                write_fail_and_insert(
                    duser_input=duser_input,
                    base=idp_item,
                    code=pre_code,
                    message=msg,
                    attach_file=None,
                    receipt_index=idp_item.get("RECEIPT_INDEX"),
                )
            except Exception:
                logger.exception("[WARN] 실패 요약 기록 중 예외 (전처리 실패)")
            idp_item["has_error"] = True
            idp_item["error_message"] = msg
            return idp_item

        # 1) OCR (Azure)
        if run_azure_ocr is None:
            raise RuntimeError("run_azure_ocr 함수 import 실패")

        ocr_in = {**idp_item}  # 필요 시 필드 축약/확장 가능
        ocr_out = run_azure_ocr(duser_input, ocr_in)

        if isinstance(ocr_out, dict) and str(ocr_out.get("RESULT_CODE")) in ("AZURE_ERR", "500"):
            msg = ocr_out.get("RESULT_MESSAGE", "Azure OCR 실패")
            logger.warning(f"[ERROR] Azure OCR 실패: {fiid}-{line_idx}-{rcp_idx} / {msg}")
            try:
                write_fail_and_insert(
                    duser_input=duser_input,
                    base=idp_item,
                    code=str(ocr_out.get("RESULT_CODE", "AZURE_ERR")),
                    message=msg,
                    attach_file=None,
                    receipt_index=idp_item.get("RECEIPT_INDEX"),
                )
            except Exception:
                logger.exception("[WARN] 실패 요약 기록 중 예외 (OCR 실패)")
            idp_item["has_error"] = True
            idp_item["error_message"] = msg
            return idp_item

        # 2) 후처리
        if post_process_and_save is None:
            raise RuntimeError("post_process_and_save 함수 import 실패")

        # OCR JSON 경로 추정/결정
        azure_dir = duser_input.get("idp_azure_dir") or os.path.join(duser_input["idp_workspace_dir"], "Azure")
        os.makedirs(azure_dir, exist_ok=True)
        try:
            base_name = Path(idp_item.get("file_path") or "").stem or f"{fiid}_{line_idx}_{rcp_idx}"
        except Exception:
            base_name = f"{fiid}_{line_idx}_{rcp_idx}"
        ocr_json_path = os.path.join(azure_dir, f"{base_name}.ocr.json")

        post_json_path = post_process_and_save(
            {**duser_input, "idp_postprocess_dir": duser_input.get("idp_postprocess_dir")},
            {**idp_item, "json_path": ocr_json_path}
        )

        # 3) DB 저장
        if insert_postprocessed_result is None:
            raise RuntimeError("insert_postprocessed_result 함수 import 실패")
        insert_postprocessed_result(post_json_path, duser_input)

        idp_item["has_error"] = False
        idp_item["error_message"] = None
        logger.info(f"[성공] execute_worker item={fiid}-{line_idx}-{rcp_idx}")

    except Exception as e:
        logger.error(f"[FATAL] execute_worker 예외: {e}", exc_info=True)
        idp_item["has_error"] = True
        idp_item["error_message"] = str(e)

    finally:
        # (옵션) 실행 이력 종료 기록
        # _write_history_end(idp_item)
        logger.info(f"[종료] execute_worker item={fiid}-{line_idx}-{rcp_idx}")

    return idp_item
    
# 실패 요약 파일 생성 + DB 입력 (idp_item 기반 단일 인자)
from typing import Dict, Any, Optional
import os, json, logging
from datetime import datetime

logger = logging.getLogger("EXTRACTOR")

def write_fail_and_insert(duser_input: Dict[str, Any], idp_item: Dict[str, Any]) -> None:
    """
    idp_item에 이미 모든 정보(FIID, LINE_INDEX, RECEIPT_INDEX, COMMON_YN, GUBUN,
    RESULT_CODE, RESULT_MESSAGE, ATTACH_FILE/source_url/file_path)가 있다고 가정.
    - 실패 요약 JSON 생성 (./Error 또는 duser_input['idp_error_dir'])
    - insert_postprocessed_result(...)로 DB 입력 (있으면)
    예외 발생 시 로깅 후 안전히 반환.
    """
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 식별자/메타
        fiid: Optional[str] = idp_item.get("FIID")
        line_index: Optional[int] = idp_item.get("LINE_INDEX")
        r_idx: int = int(idp_item.get("RECEIPT_INDEX", 0))
        common_yn: Optional[str] = idp_item.get("COMMON_YN")
        gubun: Optional[str] = idp_item.get("GUBUN")

        # 실패 코드/메시지 (기본값 안전화)
        result_code: str = str(idp_item.get("RESULT_CODE", "500"))
        result_msg: str = idp_item.get("RESULT_MESSAGE") or idp_item.get("error_message") or "Processing Failed"

        # 첨부/경로 정보 우선순위
        attach_file = (
            idp_item.get("ATTACH_FILE")
            or idp_item.get("source_url")
            or idp_item.get("file_path")
        )

        # 에러 디렉터리
        err_dir = duser_input.get("idp_error_dir") \
                  or os.path.join(duser_input.get("idp_workspace_dir", "."), "Error")
        os.makedirs(err_dir, exist_ok=True)

        # 실패 요약 내용
        summary = {
            "FIID": fiid,
            "LINE_INDEX": line_index,
            "COMMON_YN": common_yn,
            "GUBUN": gubun,
            "ATTACH_FILE": attach_file,
            "COUNTRY": None,
            "RECEIPT_TYPE": None,
            "MERCHANT_NAME": None,
            "MERCHANT_PHONE_NO": None,
            "DELIVERY_ADDR": None,
            "TRANSACTION_DATE": None,
            "TRANSACTION_TIME": None,
            "TOTAL_AMOUNT": None,
            "SUMTOTAL_AMOUNT": None,
            "TAX_AMOUNT": None,
            "BIZ_NO": None,
            "RESULT_CODE": result_code,
            "RESULT_MESSAGE": result_msg,
            "CREATE_DATE": now_str,
            "UPDATE_DATE": now_str,
            "CONTENTS": None,
        }

        # 파일 저장
        fail_name = f"fail_{fiid}_{line_index}_{r_idx}_post.json"
        fail_path = os.path.join(err_dir, fail_name)

        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "items": []}, f, ensure_ascii=False, indent=2)

        # DB 입력 시도 (모듈이 로드되어 있다면)
        try:
            # 전역/상위 스코프에 이미 import 되어 있다고 가정:
            # from db_master import insert_postprocessed_result
            if 'insert_postprocessed_result' in globals() and callable(globals()['insert_postprocessed_result']):
                globals()['insert_postprocessed_result'](fail_path, duser_input)
            else:
                logger.warning("[WARN] insert_postprocessed_result 미로드 - DB 입력 생략")
        except Exception:
            logger.exception("[WARN] 실패 요약 DB 입력 실패")

        logger.info(f"[FAIL-SAVED] {fail_path}")

    except Exception:
        logger.exception("[WARN] 실패 요약 파일 생성 실패")
    
# pre_pre_process.py (또는 전처리 모듈 파일)
from typing import Dict, Any, List, Optional
import os
import logging

logger = logging.getLogger("PRE_PROCESS")

def _make_fail_crop(data_record: Dict[str, Any], msg: str) -> Dict[str, Any]:
    """전처리 실패 시에도 항상 크롭 아이템 1개를 반환하기 위한 헬퍼"""
    return {
        "FIID": data_record.get("FIID"),
        "LINE_INDEX": data_record.get("LINE_INDEX"),
        "RECEIPT_INDEX": data_record.get("RECEIPT_INDEX", 0),
        "COMMON_YN": data_record.get("COMMON_YN"),
        "GUBUN": data_record.get("GUBUN"),
        "file_path": None,                  # 전처리 산출물 없음
        "source_url": data_record.get("ATTACH_FILE") or data_record.get("FILE_PATH"),
        "RESULT_CODE": "500",
        "RESULT_MESSAGE": f"Preprocess failed: {msg}",
    }

def run_pre_process(duser_input: Dict[str, Any], data_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    전처리 성공 시: list[dict] (각 dict는 정상 크롭, RESULT_CODE 기본 '200')
    전처리 실패/예외/빈 결과 시: 실패 크롭 1건을 담은 list[dict] 반환
    """
    try:
        # --- 기존 전처리 로직 (다운로드/병합/크롭 등) ---
        # 아래 두 줄은 "예시" 자리. 네 원래 구현을 호출/삽입해.
        # cropped_list = <원래_전처리_구현>(duser_input, data_record)
        # cropped_list: List[Dict[str, Any]]  # 전제

        cropped_list = []  # <-- 여기는 네 기존 구현으로 대체

        # 빈 결과도 실패로 간주하여 1건 반환
        if not cropped_list:
            logger.warning(
                f"[PRE] no cropped output: FIID={data_record.get('FIID')}, "
                f"LINE_INDEX={data_record.get('LINE_INDEX')}"
            )
            return [_make_fail_crop(data_record, "no cropped output")]

        # 정상 결과 정규화: 필수 키 채우고 RESULT_CODE 기본 '200'
        normalized: List[Dict[str, Any]] = []
        for c in cropped_list:
            result_code = str(c.get("RESULT_CODE", "200"))
            result_msg = c.get("RESULT_MESSAGE")
            normalized.append({
                "FIID": c.get("FIID", data_record.get("FIID")),
                "LINE_INDEX": c.get("LINE_INDEX", data_record.get("LINE_INDEX")),
                "RECEIPT_INDEX": c.get("RECEIPT_INDEX", data_record.get("RECEIPT_INDEX", 1)),
                "COMMON_YN": c.get("COMMON_YN", data_record.get("COMMON_YN")),
                "GUBUN": c.get("GUBUN", data_record.get("GUBUN")),
                "file_path": c.get("file_path"),
                "source_url": c.get("source_url", data_record.get("ATTACH_FILE") or data_record.get("FILE_PATH")),
                "RESULT_CODE": result_code,
                "RESULT_MESSAGE": result_msg,
            })
        return normalized

    except Exception as e:
        logger.exception(
            f"[PRE] exception: FIID={data_record.get('FIID')}, "
            f"LINE_INDEX={data_record.get('LINE_INDEX')}, err={e}"
        )
        # 예외도 실패 크롭 1건으로 반환
        return [_make_fail_crop(data_record, str(e))]
