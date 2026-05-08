#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo ">>> Build + up (docker-compose.logos.yml)..."
docker compose -f docker-compose.logos.yml up --build -d

echo ">>> Aguardando health..."
ok=0
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8000/auditoria/health" >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" != 1 ]; then
  echo "Health não respondeu. Logs:"
  docker compose -f docker-compose.logos.yml logs --tail 80 auditoria
  exit 1
fi

echo "OK: http://localhost:8000/auditoria/health"
echo "Docs: http://localhost:8000/docs"
