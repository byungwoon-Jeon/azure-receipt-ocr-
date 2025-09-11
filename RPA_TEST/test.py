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
    
    