# PERFORMANCE BASELINE 2.0

| Métrica | Valor | Meta |
|---------|-------|------|
| Snapshot HIT rede | **13.5 ms** | < 500ms ✅ |
| Snapshot MISS | ~425 ms (warm) | background refresh |
| F01.4-D build direct | ~30 s | refresh background |
| Finance Center first paint | Snapshot First | TTL 300s |

Evidência: `scripts/f01_snapshot_miss_hit.json`
