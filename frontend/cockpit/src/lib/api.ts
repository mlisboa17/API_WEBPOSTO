import type { AdelaideMetrics, Periodo } from "@/types/metrics";

const API_BASE =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8050"
    : "";

export async function fetchMetrics(
  periodo: Periodo = "hoje",
  grupos?: string[],
): Promise<AdelaideMetrics> {
  const params = new URLSearchParams({ periodo });
  if (grupos?.length) params.set("grupos", grupos.join(","));

  const res = await fetch(`${API_BASE}/api/v1/adelaide/metrics?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Métricas indisponíveis (${res.status})`);
  }
  return res.json();
}

export async function fetchHealth(): Promise<{ ok: boolean; detail?: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return res.json();
}

export async function fetchWebPostoHealth(): Promise<{ ok: boolean }> {
  const res = await fetch(`${API_BASE}/api/health/webposto`, {
    cache: "no-store",
  });
  return res.json();
}
