import type { AbastecimentoRow } from "@/lib/abastecimento-aggregate";

const API_BASE =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8050"
    : "";

interface ProxyV1Response {
  status_code: number;
  data?: {
    resultados?: AbastecimentoRow[];
    ultimoCodigo?: string | number | null;
  };
  detail?: string;
}

function extractRows(payload: ProxyV1Response["data"]): {
  rows: AbastecimentoRow[];
  ultimoCodigo: string | number | null | undefined;
} {
  if (!payload) return { rows: [], ultimoCodigo: null };
  const rows = Array.isArray(payload.resultados) ? payload.resultados : [];
  return { rows, ultimoCodigo: payload.ultimoCodigo };
}

export async function fetchAllAbastecimentos(
  dataInicial: string,
  dataFinal: string,
): Promise<AbastecimentoRow[]> {
  const todas: AbastecimentoRow[] = [];
  let ultimoCodigo: string | number | null | undefined = null;
  let prev: string | number | null | undefined = null;
  const maxPages = 80;

  for (let i = 0; i < maxPages; i++) {
    const params = new URLSearchParams({
      dataInicial,
      dataFinal,
      tamanhoPagina: "200",
    });
    if (ultimoCodigo != null && ultimoCodigo !== "") {
      params.set("ultimoCodigo", String(ultimoCodigo));
    }

    const res = await fetch(
      `${API_BASE}/api/v1/proxy/ABASTECIMENTO?${params.toString()}`,
      { cache: "no-store" },
    );

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Abastecimento indisponível (${res.status}): ${err.slice(0, 200)}`);
    }

    const json: ProxyV1Response = await res.json();
    const { rows, ultimoCodigo: novo } = extractRows(json.data);

    if (!rows.length) break;
    todas.push(...rows);

    if (novo == null || novo === "" || novo === prev) break;
    prev = ultimoCodigo;
    ultimoCodigo = novo;
  }

  return todas;
}
