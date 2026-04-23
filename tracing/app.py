```python
import sys
from pathlib import Path
import os

script_path = Path(__file__).resolve()
APP_PATH = None
APP_ENV = None

API_ENV = os.environ.get("API_ENV", "LOCAL")
PATH_DRIVE = "/mnt/rpa_runnerAgent"

if API_ENV == "DEV":
    APP_ENV = "DEV"
    APP_PATH = f"{PATH_DRIVE}/IDP_Python_Script/DEV"

elif API_ENV == "PRD":
    APP_ENV = "PRD"
    APP_PATH = f"{PATH_DRIVE}/IDP_Python_Script/PRD"

else: 
    PATH_DRIVE = "X:/"
    for parent in script_path.parents:
        if parent.name in ("src", "DEV", "PRD"):
            APP_ENV = parent.name.upper()
            APP_PATH = str(parent)
            break

sys.path.append(APP_PATH)

from loguru import logger

# log_path, log_format (생략 유지)
logger.remove()
# logger.add(sys.stdout, level="DEBUG", format=log_format)

from fastapi_offline import FastAPIOffline

# 1. 기존 비동기 익스큐터 (유지)
from rpa.ai.idp.api.endpoints.private.v1 import idp_executor

# 2. [추가] 신규 동기 익스큐터 임포트
from rpa.ai.idp.api.endpoints.private.v1 import idp_sync_executor

app = FastAPIOffline(
    title="SK Hynix IDP API",
    description="Sample API service",
    version="1.0",
    root_path={"LOCAL":"/api", "DEV":"/api", "STG":"/api", "PRD":"/api"}[API_ENV],
)

# 1. 기존 라우터 등록 (유지 - /v1/idp/execute 로 매핑됨)
app.include_router(idp_executor.router, prefix="/v1/idp")

# 2. [추가] 신규 동기 라우터 등록 (분기 - /v1/idp/sync/execute 로 매핑됨)
app.include_router(idp_sync_executor.router, prefix="/v1/idp/sync")

# print_message 처리 (생략 유지)
# logger.info(print_message)

```
