```python
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# 기존 경로 설정 로직 유지
script_path = Path(__file__).resolve()
app_path = None
for parent in script_path.parents:
    if parent.name in ("src", "DEV", "PRD"):
        app_path = str(parent)
        break

if app_path and app_path not in sys.path:
    sys.path.append(app_path)

# 기존 로직(executor) 임포트 (예시)
# from api.endpoints.private.v1 import idp_executor 

class SyncSystemNameHandler:
    """
    기존 비동기 로직에 영향을 주지 않는 신규 동기식 전용 핸들러
    """
    def dispatch_sync(self, request_data: dict) -> dict:
        start_time = datetime.now()
        idp_request_id = f"{start_time.strftime('%Y%m%d%H%M%S')}{int(start_time.microsecond / 1000):03d}"
        request_data["idpRequestId"] = idp_request_id

        try:
            system_name = request_data.get("systemName", "").lower()
            
            # 1. 시스템 지원 여부 체크
            if not hasattr(self, system_name):
                return self._make_response(idp_request_id, 400, f"지원하지 않는 시스템: {system_name}", request_data)

            # 2. 동적 함수 매핑 및 실행 (동기 방식)
            # BackgroundTasks 없이 함수를 직접 호출하여 리턴값을 받음
            target_func = getattr(self, system_name)
            execution_result = target_func(request_data)

            # 3. 결과 포함 응답 생성
            return self._make_response(idp_request_id, 200, "Success", execution_result)

        except Exception as e:
            logger.error(f"[Sync Dispatcher] Error: {str(e)}")
            return self._make_response(idp_request_id, 500, f"Internal Error: {str(e)}", request_data)

    def _make_response(self, req_id, code, msg, items_data):
        # 요청하신 리스폰스 형식에 맞춤
        return {
            "idpRequestID": req_id,
            "code": str(code),
            "message": msg,
            "systemName": items_data.get("systemName") if isinstance(items_data, dict) else "",
            "items": items_data.get("items") if isinstance(items_data, dict) else items_data
        }

    # 각 시스템별 실행 메소드 (기존 coa01 로직을 복사하거나 공통화)
    def coa01(self, request_data: dict):
        # 실제 비즈니스 로직인 executor.execute를 호출하고 결과를 'return' 함
        # result_json = she_testreport_extractor.execute(duser_input=request_data)
        # return result_json
        logger.info(f"Sync coa01 실행 시작: {request_data.get('idpRequestId')}")
        
        # 실제 구현 시에는 기존 executor의 반환값을 그대로 리턴하도록 작성
        return request_data.get("items", []) 

```
