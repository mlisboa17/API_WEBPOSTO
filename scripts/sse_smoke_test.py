from fastapi.testclient import TestClient
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://webposto:changeme@localhost:5433/webposto")

import main

client = TestClient(main.app)

with client.stream("GET", "/api/stream") as response:
    print("status", response.status_code)
    print("ctype", response.headers.get("content-type", ""))
    first_line = next(response.iter_lines())
    print("first_line", first_line)
