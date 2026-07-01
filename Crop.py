요청 사항 확인: 현재 SK하이닉스 현장과 같이 외부망 및 API 접근 권한이 철저히 통제된 환경에서, 오직 파드 내부 쉘(exec) 접속 및 애플리케이션 로그만을 활용하여 1) 메모리 증량 근거를 확보하고 2) 파이썬 메모리 누수를 탐지하는 방법을 요청하셨습니다. 해당 제약 사항을 100% 이해했습니다.
### 핵심 요약 (결론)
 * **메모리 증량 근거:** K8s 외부 API를 쓸 수 없으므로, 파드 내부의 **Cgroup(Control Group) 파일**을 직접 읽어 컨테이너에 할당된 '메모리 한계치(Limit)' 대비 '실제 사용량(Usage)'이 100%에 도달했음을 캡처하거나 애플리케이션 로그로 남겨야 합니다.
 * **메모리 누수 탐지:** OS 레벨 명령어(top, ps)는 순간적인 상태만 보여주므로, 파이썬 코드 내부에 tracemalloc 로직을 백그라운드 스레드로 삽입하여 **정기적인 메모리 할당 스냅샷을 표준 출력(stdout) 로그로 남기는 방식**으로 전환해야 합니다.
> **비판적 시각에서의 문제 제기 (Risk Point)**
> 파드 내부에서 텍스트 파일 등으로 누수 기록을 남기더라도, 실제 메모리가 가득 차서 OOM(Out Of Memory) 킬이 발생하면 **파드가 재시작되면서 내부의 임시 데이터는 모두 삭제됩니다.** 따라서 증량 근거와 누수 로그는 반드시 파드 내부 저장이 아닌, 파이썬 표준 출력(stdout) 방식을 사용하여 외부 중앙 로그 시스템에 안전하게 기록되도록 설계해야 합니다.
> 
### 1. 파드 내부에서 메모리 증량 근거 확보 방안
free -m과 같은 명령어는 컨테이너가 아닌 호스트(노드) 전체의 메모리를 보여주므로 증거로 무효합니다. 반드시 컨테이너 제어 그룹인 cgroup 메트릭을 확인해야 합니다.
**A. Cgroup 파일 직접 조회 (파드 쉘 접속 시)**
파드 내부에 접속하여 다음 명령어를 실행하고, Limit 값과 Usage 값이 동일해지는(OOM 직전) 시점을 캡처하여 보고서에 첨부합니다.
 * **Cgroup v2 환경 (최근 K8s 표준):**
   * 할당된 최대 메모리: cat /sys/fs/cgroup/memory.max
   * 현재 사용 중인 메모리: cat /sys/fs/cgroup/memory.current
 * **Cgroup v1 환경:**
   * 할당된 최대 메모리: cat /sys/fs/cgroup/memory/memory.limit_in_bytes
   * 현재 사용 중인 메모리: cat /sys/fs/cgroup/memory/memory.usage_in_bytes
**B. 파이썬 코드 기반 자동 로깅 (권장)**
OOM으로 파드가 죽기 직전의 상황을 확실히 증명하기 위해, 파이썬 코드 레벨에서 메모리 사용량을 주기적으로 로깅하는 로직을 추가합니다.
```python
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)

def log_cgroup_memory():
    while True:
        try:
            # Cgroup v2 기준 (v1인 경우 경로 수정 필요)
            with open('/sys/fs/cgroup/memory.current', 'r') as f:
                current_mem = int(f.read().strip()) / (1024 * 1024) # MB 단위
            with open('/sys/fs/cgroup/memory.max', 'r') as f:
                max_mem_str = f.read().strip()
                max_mem = "No Limit" if max_mem_str == "max" else int(max_mem_str) / (1024 * 1024)
            
            logging.info(f"[Memory Proof] Current: {current_mem:.2f} MB / Limit: {max_mem} MB")
        except Exception as e:
            pass
        
        time.sleep(60) # 1분 간격으로 증명 데이터 적재

# 애플리케이션 시작점에 스레드 실행 추가
threading.Thread(target=log_cgroup_memory, daemon=True).start()

```
### 2. 파드 내부에서 파이썬 메모리 누수 탐지 방안
파드 내부에서는 kubectl top과 같은 트레이싱 도구를 쓸 수 없으므로, 파이썬의 tracemalloc 라이브러리를 활용해 로그 스트림으로 누수 지점을 쏘아 올려야 합니다.
**A. tracemalloc 로그 자동화 스냅샷**
메모리가 비정상적으로 증가하는 객체를 찾아내기 위해 일정 주기마다 메모리 할당 차이(Diff)를 계산합니다.
```python
import tracemalloc
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
tracemalloc.start()

def trace_memory_leak():
    snapshot1 = tracemalloc.take_snapshot()
    while True:
        time.sleep(300) # 5분 간격 비교 (운영 상황에 맞게 조절)
        snapshot2 = tracemalloc.take_snapshot()
        
        # 이전 스냅샷과 비교하여 가장 많이 증가한 상위 5개 라인 추출
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        logging.info("=== [Memory Leak Detection: Top 5] ===")
        for stat in top_stats[:5]:
            logging.info(stat)
        
        # 기준 스냅샷 갱신
        snapshot1 = snapshot2

threading.Thread(target=trace_memory_leak, daemon=True).start()

```
 * **로그 해석 방법:** 5분마다 출력되는 로그 중, 특정 파일의 특정 라인(예: data_processor.py:45)에 할당된 크기(KiB/MiB)가 시간이 지남에 따라 줄어들지 않고 계속 누적 증가한다면 해당 코드가 누수 발생 지점입니다.
**신뢰도 점수: 9/10**
클러스터 제어 권한이 없을 때 컨테이너 내부의 Cgroup 파일을 읽어 모니터링을 대체하는 것은 리눅스 컨테이너 환경의 가장 원초적이고 확실한 표준 우회 방법입니다. 단, 현재 구동 중인 K8s 노드의 OS 환경에 따라 Cgroup v1과 v2 중 어떤 것이 마운트되어 있는지 즉각적인 확인이 어려워 파일 경로 확인 작업이 선행되어야 하므로 1점 차감했습니다. 보완을 위해 파드 내부 쉘에서 ls /sys/fs/cgroup 명령어를 입력하여 현재 환경의 Cgroup 버전을 먼저 확인하시기 바랍니다.
현재 애플리케이션에서 출력하는 이 표준 로그(stdout)들은 파드가 OOM으로 강제 종료되더라도 사후에 분석할 수 있도록 사내 중앙 로그 시스템(예: ELK, Datadog 등)에 실시간으로 수집되고 있습니까?
