```python
from loguru import logger
from fastapi import APIRouter, Request

# (가정) 이전에 논의한 동기식 핸들러를 임포트
# 실제 경로에 맞게 수정 필요
from rpa.ai.idp.api.services.private.v1.idp_sync_dispatcher import SyncSystemNameHandler

# OpenAPI 스키마 (필요시 동기식 전용으로 분리 권장)
from rpa.ai.idp.api.models.private.v1.schemas import execute_method_openapi_extra

router = APIRouter()

@router.post(
    "/execute",
    summary="[동기식] 각 부서 업무별 서비스 호출",
    description="작업을 즉시 수행하고 결과를 response body에 포함하여 반환합니다.",
    openapi_extra=execute_method_openapi_extra,
)
def execute_sync(request_data: dict, request: Request) -> dict:
    """
    동기식 실행 엔드포인트.
    BackgroundTasks를 사용하지 않고, 로직이 끝날 때까지 대기 후 결과 반환.
    """
    logger.info(f"POST /sync/execute - Client:{request.client.host}")
    
    # 동기식 전용 핸들러 호출
    handler = SyncSystemNameHandler()
    
    # 결과를 직접 반환받음 (BackgroundTasks 없음)
    response_data = handler.dispatch_sync(request_data)
    
    return response_data

```
