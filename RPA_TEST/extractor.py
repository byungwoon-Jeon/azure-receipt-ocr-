###Initializing runtime enviroment###
import sys
from pathlib import Path

script_path = Path(__file__).resolve()

for parent in script_path.parents:
    if parent.name in ("src", "DEX", "PEX"):
        app_path = str(parent)
        break

if not app_path:
    raise FileNotFoundError(f"ERR")

if app_path not in sys.path:
    sys.path.append(app_path)

from rpa.ai.idp.util import idp_setup_env, idp_utils
from logru import logger

working_path: dict = idp_setup_env.initialize_working_paths(script_path.parent)

idp_utils.setup_logger(log_level="DEBUG",log_path=working_path["idp_log_file_path"])

import logging

###User Define Function###
import os
import re
import json
import tomlkit
from datetime import datetime 

from db_master import query_data_by_date, insert_postprocessed_result
from pre_pre_process import run_pre_pre_process    # Integrated pre-processing + YOLO
from doc_process import run_azure_ocr
from post_process import post_process_and_save
from typing import Optional

#
#
def _adapter_run_pre_process(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    각 data_record를 받아 run_pre_process를 실행하는 '단일 태스크'.
    입력: {"duser_input": dict, "data_record": dict}
    출력: {"cropped_list": list[dict], "error": str|None}
    """
    duser_input = params["duser_input"]
    data_record = params["data_record"]
    try:
        cropped_list = run_pre_process(duser_input, data_record)  # 반드시 list[dict]
        if not isinstance(cropped_list, list):
            raise TypeError("run_pre_process must return list[dict]")
        return {"cropped_list": cropped_list or [], "error": None}
    except Exception as e:
        logger.exception(
            f"[PRE] run_pre_process 실패: FIID={data_record.get('FIID')}, LINE_INDEX={data_record.get('LINE_INDEX')}, err={e}"
        )
        return {"cropped_list": [], "error": str(e)}


def generate_idp_items(duser_input: Dict[str, Any],
                       data_records: List[Dict[str, Any]],
                       include_failed: bool = False) -> List[Dict[str, Any]]:
    """
    data_records의 '반복 자체'를 스레드로 병렬 실행하여 run_pre_process를 동시에 호출하고,
    각 결과(cropped_list: list[dict])를 평탄화하여 OCR 대상 아이템(idp_items)을 만든다.

    - ATTACH_FILE 제외
    - RESULT_CODE / RESULT_MESSAGE 추가
    - include_failed=False 이면 RESULT_CODE != "200" 항목은 제외
    - 순서 보장 없음(필요하면 pre_results 정렬 한 줄 추가 가능)
    """
    idp_items: List[Dict[str, Any]] = []
    if not data_records:
        logger.info("generate_idp_items: data_records 비어 있음")
        return idp_items

    # 1) '레코드 단위 반복 자체'를 병렬화: 각 record → 하나의 태스크
    thread_params = [{"duser_input": duser_input, "data_record": rec} for rec in data_records]
    pre_results = idp_utils.run_in_multi_thread(_adapter_run_pre_process, thread_params)

    # (선택) 순서 보장 원하면 아래 주석 해제
    # pre_results.sort(key=lambda r: (r.get("error") is not None))

    # 2) 평탄화(flatten) → idp_items
    item_seq = 1
    for res in pre_results:
        if res["error"]:
            # 전처리 자체 실패: 스킵 (실패를 아이템에 포함하려면 여기서 생성도 가능)
            continue

        cropped_list: List[Dict[str, Any]] = res["cropped_list"]
        if not cropped_list:
            continue

        for cropped in cropped_list:
            # 전처리 단계가 RESULT_CODE/RESULT_MESSAGE를 넣어줬다고 가정
            result_code = str(cropped.get("RESULT_CODE", "200"))
            result_msg = cropped.get("RESULT_MESSAGE")

            if (result_code != "200") and not include_failed:
                continue

            idp_items.append({
                "item_seq": item_seq,                        # 생성 시점의 전역 순번
                "FIID": cropped.get("FIID"),
                "LINE_INDEX": cropped.get("LINE_INDEX"),
                "RECEIPT_INDEX": cropped.get("RECEIPT_INDEX"),
                "COMMON_YN": cropped.get("COMMON_YN"),
                "GUBUN": cropped.get("GUBUN"),
                "file_path": cropped.get("file_path"),       # 전처리 산출물(크롭 이미지) 경로
                "RESULT_CODE": result_code,                  # 요청 반영
                "RESULT_MESSAGE": result_msg,                # 요청 반영
                "has_error": (result_code != "200"),
                "error_message": result_msg if result_code != "200" else None,
            })
            item_seq += 1

    logger.info(f"generate_idp_items: 총 {len(idp_items)}개 아이템 생성 (records={len(data_records)})")
    return idp_items

#
#
def write_fail_and_insert(duser_input: dict,
    						base: dict,
                            code: str,
                            message: str,
                            attach_file:Optional[str]=None,
                            receipt_index:Optional[str]=None):
	
    now_str=datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    fiid = base.get("FIID")
    line_index = base.get("LINE_INDEX")
    r_idx = receipt_index if receipt_index is not None else base.get("RECEIPT_INDEX")
    
    summary = {
    	"FIID":fiid,
        "LINE_INDEX":line_index,
        "COMMON_YN":base.get("COMMON_YN"),
        "GUBUN" : base.get("GUBUN"),
        "ATTACH_FILE":attach_file,
        "COUNTRY":None, "RECEIPT_TYPE" : None, "MERCHANT_NAME":None,"MERCHANT_PHONE_NO":None,
        "DELIVERY_ADDR":None, "TRANSACTION_DATE":None, "TRANSACTION_TIME":None,
        "TOTAL_AMOUNT":None, "SUMTOTAL_AMOUNT":None, "TAX_AMOUNT":None, "BIZ_NO":None,
        RESULT_CODE:code,
        RESULT_MESSAGE:message,
        CREATE_DATE:now_str,
        UPDATE_DATE:now_str,
        "CONTENTS":None
    }
    
    os.makedirs(duser_input["idp_error_dir"], exit_ok=True)
    fail_name = f"fail_{fiid}_{line_index}_{r_idx if r_idx is not None else 0}_post.json"
    fail_path = os.path.join(duser_input["idp_error_dir"],fail_name)
    with open(fail_path, "w", encoding="utf-8") as f :
    	json.dump({"summary":summary, "items":[]}, f, ensure_asci=False, indent=2)
    
    try:
        inset_postprocessed_reuslt(fail_path,duser_input)
    except Exception as e:
        logger.error("error")    

#
#
def execute_worker(record: dict, duser_input: dict):
    """
    하나의 DB 레코드에 대해 전체 OCR 파이프라인 단계를 실행합니다.
    전처리(다운로드 및 YOLO 크롭), Azure OCR 인식, 후처리 및 DB 저장까지 순차적으로 수행하며, 각 단계의 결과에 따라 오류 시 다음 단계를 건너뜁니다.

    입력:
    - record (dict): 처리할 단일 레코드 (FIID, LINE_INDEX, GUBUN, ATTACH_FILE, FILE_PATH 등 포함).
    - duser_input (dict): 파이프라인 실행에 필요한 설정 정보가 담긴 딕셔너리 (DB 연결, 경로, Azure OCR 키 등).

    출력:
    - None: 처리는 부수 효과(파일 저장, DB 입력)로 이루어지며, 함수 자체는 값을 반환하지 않습니다. (오류 발생 시 내부적으로 로그를 기록합니다)
    """
    logger.info(f"[시작] process_single_record - FIID={record.get('FIID')}, LINE_INDEX={record.get('LINE_INDEX')}")
    try:
     #  #전처리 단계 실행 (다운로드 + 크롭)
        cropped_list = run_pre_pre_process(duser_input, record)

		# 전처리 단계 실패
        if not cropped_list:
            for key, r_idx, c_yn in [("ATTACH_FILE", 1, "N"), ("FILE_PATH",1,"Y")]:
                url = record.get(key)
                if not url:
                    continue
                write_fail_and_insert(
                	duser_input=duser_input,
                    base={"FIID":record.get("FIID"),
                    "LINE_INDEX":record.get("LINE_INDEX"),
                    "GUBUN":record.get("GUBUN"),
                    "COMMON_YN":c_yn,
                    "RECEIPT_INDEX":r_idx},
                    code="500",
                    message="전처리 단계 실패",
                    attach_file=url,
                    receipt_index=r_idx
                    )
                return

        for cropped in cropped_list:
            if "RESULT_CODE" in cropped:
                logger.warning(f"[SKIP] YOLO 오류 발생: {cropped}")
                write_fail_and_insert(
                	duser_input=duser_input,
                    base={"FIID":cropped.get("FIID"),
                    "LINE_INDEX":cropped.get("LINE_INDEX"),
                    "GUBUN":cropped.get("GUBUN"),
                    "COMMON_YN":cropped.get("COMMON_YN"),
                    "RECEIPT_INDEX":cropped.get("RECEIPT_INDEX")},
                    code=cropped.get("RESULT_CODE", 500),
                    message=cropped.get("RESULT_MESSAGE", "YOLO 단계 오류"),
                    attach_file=cropped.get("source_url"),
                    receipt_index=cropped.get("RECEIPT_INDEX")
                )
                continue

            # OCR 실행 ✅ 수정 코드:
            ocr_result = run_azure_ocr(duser_input, cropped)
            if ocr_result.get("RESULT_CODE") == "AZURE_ERR":
                logger.warning(f"[ERROR] Azure OCR 실패 → 오류 summary 저장 시도")

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error_summary = {
                    "FIID": cropped.get("FIID"),
                    "LINE_INDEX": cropped.get("LINE_INDEX"),
                    "RECEIPT_INDEX": cropped.get("RECEIPT_INDEX"),
                    "COMMON_YN": cropped.get("COMMON_YN"),
                    "GUBUN": cropped.get("GUBUN"),
                    "ATTACH_FILE": record.get("ATTACH_FILE"),
                    "COUNTRY": None, "RECEIPT_TYPE": None, "MERCHANT_NAME": None, "MERCHANT_PHONE_NO": None,
                    "DELIVERY_ADDR": None, "TRANSACTION_DATE": None, "TRANSACTION_TIME": None,
                    "TOTAL_AMOUNT": None, "SUMTOTAL_AMOUNT": None, "TAX_AMOUNT": None, "BIZ_NO": None,
                    "RESULT_CODE": ocr_result.get("RESULT_CODE"),
                    "RESULT_MESSAGE": ocr_result.get("RESULT_MESSAGE"),
                    "CREATE_DATE": now_str,
                    "UPDATE_DATE": now_str
                }

                error_result_path = os.path.join(
                    duser_input["post_json_dir"],
                    f"fail_{error_summary['FIID']}_{error_summary['LINE_INDEX']}_{error_summary['RECEIPT_INDEX']}_post.json"
                )
                with open(error_result_path, "w", encoding="utf-8") as f:
                    json.dump({"summary": error_summary, "items": []}, f, ensure_ascii=False, indent=2)

                insert_postprocessed_result(error_result_path, duser_input)
                continue

            # 후처리 JSON 경로 구성
            json_path = os.path.join(
                duser_input["idp_azure_dir"],
                f"{os.path.splitext(os.path.basename(cropped['file_path']))[0]}.ocr.json"
            )

            # 후처리 실행
            post_json_path = post_process_and_save(
                {**duser_input, "idp_postprocess_dir": duser_input["idp_postprocess_dir"]},
                {**cropped, "json_path": json_path, "ATTACH_FILE": cropped.get("source_url")}
            )

            # DB 저장
            insert_postprocessed_result(post_json_path, duser_input)

    except Exception as e:
        logger.error(f"[FATAL] 처리 중 오류 발생 - FIID={record.get('FIID')}: {e}", exc_info=True)
    logger.info(f"[종료] process_single_record - FIID={record.get('FIID')}, LINE_INDEX={record.get('LINE_INDEX')}")

#
#
def _adapter_excute_worker(params:dict):
    record = params["record"]
    duser_input = params["duser_input"]
    retrun execute_worker(record, duser_input)

#
#
def das_process_setup(duser_input:dict) -> dict:
    try :
        logger.debug(f"DAS 프로세스 환경설정 시작")
        
        idp_filedrop_dir = duser_input["idp_filedrop_dir"]    
        idp_output_files_dir = duser_input["idp_output_files_dir"]
        idp_log_file_path = duser_input["idp_log_file_path"]
        
        sub_folder_name = datetime.now().strtime("%Y%m%d")
        
        idp_workspace_dir = os.path.join(idp_filedrop_dir, sub_folder_name)
        idp_preprocess_dir = os.path.join(idp_workspace_dir, "PreProcess")
        idp_docprocess_dir = os.path.join(idp_workspace_dir, "DocProcess")
        idp_postprocess_dir = os.path.join(idp_workspace_dir, "PostProcess")
        
        idp_rawfile_dir = os.path.join(idp_workspace_dir, "RawFile")
        idp_mergerdoc_dir = os.path.join(idp_prerpocess_dir, "MergeDoc")
        idp_cropped_dir = os.path.join(idp_preprocess_dir, "Cropped")
        idp_azure_dir = os.path.join(idp_docprocess_dir, "Azure")
        idp_error_dir = os.path.join(idp_docprocess_dir, "Error")
        if not os.path.exists(idp_workspace_dir):
            os.mkdir(idp_workspace_dir)
        if not os.path.exists(idp_preprocess_dir):
            os.mkdir(idp_preprocess_dir)
        if not os.path.exists(idp_docprocess_dir):
            os.mkdir(idp_docprocess_dir)
        if not os.path.exists(idp_postprocess_dir):
            os.mkdir(idp_postprocess_dir)
            
        if not os.path.exists(idp_rawfile_dir):
            os.mkdir(idp_rawfile_dir)
        if not os.path.exists(idp_mergedoc_dir):
            os.mkdir(idp_mergedoc_dir)
        if not os.path.exists(idp_cropped_dir):
            os.mkdir(idp_cropped_dir)
        if not os.path.exists(idp_azure_dir):
            os.mkdir(idp_azure_dir)
        if not os.path.exists(idp_error_dir):
            os.mkdir(idp_error_dir)     
    except Exception:
        logger("error")

#
#
def execute(duser_input: dict):
    """
    지정한 날짜에 해당하는 모든 DB 레코드를 조회하여 OCR 파이프라인을 실행합니다.
    각 레코드를 별도의 스레드로 처리하며, 처리할 레코드가 없으면 함수를 종료합니다.

    입력:
    - duser_input (dict): 파이프라인 설정 및 DB 연결 정보를 담은 딕셔너리. (sqlalchemy_conn, target_date 등과 OCR/YOLO 관련 설정 포함)

    출력:
    - None: 처리 완료 후 함수는 아무 값도 반환하지 않습니다. (과정 중 로그로 진행 상황을 기록합니다)
    """
    logger.info("[시작] run_wrapper")
    
    duser_input = {**duser_input,**working_paths}
    duser_input = das_process_setup(duser_input)
    
    data_records = query_data_by_date(duser_input)
    if not data_records:
        logger.info("📭 처리할 데이터가 없습니다.")
        return

    logger.info(f"총 {len(data_records)}건 처리 시작")
    
    func_params_list = [
    	{"record":rec, "duser_input":duser_input}
        for rec in data_records
    ]
    
    idp_utils.run_in_multi_thread(
    	target_func=adapter_excute_worker,
        func_params_list=func_params_list,
    )
    
    logger.info("✅ 전체 파이프라인 완료")
    logger.info("[종료] run_wrapper")

if __name__ == "__main__":
	duser_input = {
    	"SystemName" : "DAS01",
        "ccrParams":{
        	"targetDate" : "2025-09-03"
        }
    }
	execute(duser_input)
