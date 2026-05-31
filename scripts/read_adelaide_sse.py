import sys
import requests

job_id = sys.argv[1]
r = requests.get(f"http://127.0.0.1:8010/api/adelaide/stream/{job_id}", stream=True, timeout=30)
print("status", r.status_code)
print("ctype", r.headers.get("content-type"))
seen_done = False
for raw in r.iter_lines():
    if not raw:
        continue
    line = raw.decode() if isinstance(raw, bytes) else raw
    print(line)
    if '"event": "done"' in line:
        seen_done = True
        break
print("seen_done", seen_done)
