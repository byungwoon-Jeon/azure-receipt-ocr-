```python
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# [경로 설정] 기존 프로젝트 구조 유지
script_path = Path(__file__).resolve()
app_path = None
for parent in script_path.parents:
    if parent.name in ("src", "DEV", "PRD"):
        app_path = str(parent)
        break

if app_path and app_path not in sys.path:
    sys.path.append(app_path)

# 각 시스템별 실제 비즈니스 로직(Executor) 임포트
# 예: from api.endpoints.private.v1 import she_testreport_extractor

class SyncSystemNameHandler:
    """
    기존 비동기 로직을 건드리지 않고, 결과를 즉시 반환하는 동기식 전용 핸들러.
    목표: executor.execute()의 결과(result_json)를 리턴값에 포함함.
    """
    
    def dispatch_sync(self, request_data: dict) -> dict:
        start_time = datetime.now()
        # ID 생성 로직 유지
        idp_request_id = f"{start_time.strftime('%Y%m%d%H%M%S')}{int(start_time.microsecond / 1000):03d}"
        request_data["idpRequestId"] = idp_request_id

        try:
            system_name = request_data.get("systemName", "").lower()
            
            # 1. 시스템 지원 여부 체크
            if not hasattr(self, system_name):
                return self._make_response(idp_request_id, "400", f"지원하지 않는 시스템: {system_name}", request_data)

            # 2. 동적 함수 매핑 (예: coa01)
            target_func = getattr(self, system_name)
            
            # 3. 비즈니스 로직 실행 및 결과(result_json) 수신
            # [중요] 여기서 executor.execute()의 리턴값이 반환됩니다.
            execution_result = target_func(request_data)

            # 4. 최종 결과 반환
            return self._make_response(idp_request_id, "200", "Success", execution_result)

        except Exception as e:
            logger.error(f"[Sync Dispatcher] Critical Error: {str(e)}")
            return self._make_response(idp_request_id, "500", f"Internal Server Error: {str(e)}", request_data)

    def _make_response(self, req_id, code, msg, result_data):
        """
        설계된 리스폰스 규격에 맞춰 데이터를 패키징합니다.
        result_data가 dict일 경우와 list일 경우를 모두 대응합니다.
        """
        # 기본 구조 생성
        response = {
            "idpRequestID": req_id,
            "code": str(code),
            "message": msg,
            "systemName": "",
            "items": []
        }

        if isinstance(result_data, dict):
            response["systemName"] = result_data.get("systemName", "")
            # executor가 반환한 데이터가 이미 규격을 갖춘 경우 items에 할당
            response["items"] = result_data.get("items", [result_data]) 
        else:
            # list 등의 형태일 경우 직접 할당
            response["items"] = result_data

        return response

    # ---------------------------------------------------------
    # 시스템별 실행 메소드 구역 (기존 로직의 동기 버전)
    # ---------------------------------------------------------

    def coa01(self, request_data: dict):
        """
        [SHE_CAREER01 대응] 
        기존 비동기 함수와 달리, 결과를 변수에 담아 반드시 'return' 해야 합니다.
        """
        try:
            logger.info(f"Sync Execution Start [coa01]: {request_data.get('idpRequestId')}")
            
            # [핵심] 실제 비즈니스 로직 호출 및 결과값(result_json) 저장
            # 실제 파일명에 맞춰 import 및 호출이 필요합니다.
            # 예: result_json = she_testreport_extractor.execute(duser_input=request_data)
            
            # 여기서는 예시로 로직 결과가 리턴된다고 가정합니다.
            result_json = {
                "systemName": "SHE_CAREER01",
                "items": request_data.get("items", []) # 실제로는 executor의 결과값이 들어감
            }
            
            # 결과를 위로 던져줌 (dispatch_sync로 전달)
            return result_json
            
        except Exception as e:
            logger.error(f"Error in coa01 execution: {str(e)}")
            raise e # 에러를 위로 던져서 dispatch_sync의 except문에서 처리하게 함

    # 추가적인 시스템 함수들(coa02, coa03...)도 동일한 패턴으로 작성

```
