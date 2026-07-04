import time
import httpx
from datetime import datetime, timedelta

end = datetime.now().date()
start = end - timedelta(days=7)
params = {"dataInicial": start.isoformat(), "dataFinal": end.isoformat()}
base = "http://127.0.0.1:8040/api/v1/owner-action-center"

r1 = httpx.post(f"{base}/analysis/refresh", params=params, timeout=10).json()
time.sleep(1)
s1 = httpx.get(f"{base}/analysis/status/{r1['analysis_id']}", timeout=10).json()
r2 = httpx.post(f"{base}/analysis/refresh", params=params, timeout=10).json()
print("r1", r1)
print("status1", s1)
print("r2", r2)
