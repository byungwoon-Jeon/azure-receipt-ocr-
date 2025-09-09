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

###user define function###
import json
import tomlkit
from rpa.ai.idp.she.itpassing.ppe_cert import pre_processing
from rpa.ai.idp.she.itpassing.ppe_cert import doc_processing

from rpa.ai.idp.util import idp_utils
from rpa.ai.idp.util import idp_execution_recoder as idp_recoder

#
#
def execute(duser_input:dict)->str:
    
    logger.debug(idp_setup_env.get_runtime_env())
	logger.info(f"execute method enterd.")
    logger.debug(f"duser_input:{json,dump(duser_input, indent=2, ensure_ascii=False)}")
    
    #결과반환 제이슨
    ret_json = {
    	"callback_url":None,
        "req_no":None,
        "cmd_id":None,
        "has_error":False,
        "error_message":None,
        "error_fields":None,
        "idp_items":None,
    }
    
    duser_input = {**duser_input, **working_paths}
    
    module_config_file_path, toml_data = load_module_config()
    
    try:
    	#입력 파라미터 검증
        validate_result = pre_processing.validate_required_fields(duser_input)
        
        if validate_result and validate_result["has_error"]:
            ret_json["has_error"] = True
            ret_json["error_message"] = validate_result["error_message"]
            ret_json["error_fields"] = validate_result["error_fields"]
            
            ret_str = json.dump(ret_json, indent=2, ensure_ascii=False)
            logger.info(f"execute method finish")
            return ret_str
            
        
        # 데이터 추출 시작
        # 파라미터를 작업하기 위해 아이템즈로 변환
        idp_items = pre_processing.generate_idp_items(duser_input)
        
        # 데이터 추출 시작 쓰레딩
        thread_params = [{"idp_item":idp_item, "duser_input":duser_input} for idp_item in idp_items]
        idp_items = idp_utils.run_in_multi_thread(_execute_worker_adapter, thread_params)
        
        #결과 제이슨에 아이템 추가
        ret_json["idp_items"] = idp_items
    
    except Exception:
        ret_json["has_error"] = True
        ret_json["error_message"] = "오류 발생"
        
    ret_str = json.dump(ret_json,indent=2,ensure_ascii=False)
    
    return ret_str
    
#
#    
def _excute_worker_adapter(thread_params:dict)->dict:
    return execute_worker(thread_params["idp_item"], thread_param["duser_input"])
        
    
def execute_worker(idp_item:dict, duser_input:dict) -> dict:
    logger.info(f"execute_worker method entered.")
    
    try:            
    	# 실행내역 입력시작
        idp_exe_history = {}
        # 실행 요청 아이디
        idp_exe_history["req_id"] = idp_item.get("req_id", idp_utils.get_timestamp_as_iso_format())
        # 업무 구분
        idp_exe_history["biz_cls"] = "SHE"
        # 업무 키
        idp_exe_history["biz_key"] = "_".join((idp_item["rpt_id"], idp_item["rpt_seq"]))
        # process id
        idp_exe_history["rpago_proc_id"] = idp_item["rpago_proc_id"]
        #IDP 실행순서
        idp_exe_history["exe_seq"] = idp_itemp["index"]
        #데이터 추출 대상 파일 문서 종류
        idp_exe_history["idp_type"] = "분석성적서"
        #데이터 추출 대상 파일명
        idp_exe_history["req_file_name"] = None
        #데이터 추출 대상 파일 패스
        idp_exe_history["req_file_path"] = None
        #rpago 파라미터
        idp_exe_history["biz_input"] = json.dump(duser_input)
        
        # db입력
    	try:
        	idp_recorder.write_idp_execution_history_start(idp_exe_history)
        except Exception:
            idp_item["has_error"] = True
            idp_item["error_message"] = "오류 발생"
        
        if not idp_item["has_error"]:
            idp_item = pre_processing.download_test_report(idp_item)

        if not idp_item["has_error"]:
            idp_item = doc_processing.extract_test_report(idp_item)

        if not idp_item["has_error"]:
            idp_item = post_processing.refine_doc_process_result(idp_item)

        if not idp_item["has_error"]:
            idp_item = db_manager.excute_query_post_process_result(idp_item)

        if not idp_item["has_error"]:
            idp_item = db_manager.execute_query_post_process_status(idp_item)
                                    
        finally:
        	if idp_item["has_error"] == True:
                idp_exe_history["idp_status"] = "Failure"
        	    idp_exe_history["biz_comment"] = idp_item["error_message"]
            else:
            	idp_exe_history["idp_status"] = "Success"    
            
            idp_exe_history["document_id"] = idp_item.get("document_id", None)
            idp_exe_history["req_file_name"] = idp_item.get("attach_file_name", None)
            idp_exe_history["req_file_path"] = idp_item.get("attach_file_path", None)
    
    		try:
            	idp_recoder.write_idp_execution_history_end(idp_exe_history)
            except Exception:
                logger.exception("오류")
            
        return idp_item
    
    
    
    
    
    
    
    
    