import type {
  BankMovementsResponse,
  OfxImportPayload,
  ParsedStatementTransaction,
} from "@/types/statements";

const API_BASE =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8050"
    : "";

export async function fetchBankMovements(params: {
  dataInicial: string;
  dataFinal: string;
  empresaCodigo?: string;
  page?: number;
  limit?: number;
}): Promise<BankMovementsResponse> {
  const qs = new URLSearchParams({
    dataInicial: params.dataInicial,
    dataFinal: params.dataFinal,
    page: String(params.page ?? 1),
    limit: String(params.limit ?? 50),
  });
  if (params.empresaCodigo) qs.set("empresaCodigo", params.empresaCodigo);

  const res = await fetch(`${API_BASE}/api/v1/finance/center/bank-movements?${qs}`, {
    cache: "no-store",
  });
  const body = await res.json();
  if (!res.ok || body.success === false) {
    throw new Error(body.error?.message ?? body.error ?? `Extrato indisponível (${res.status})`);
  }
  return body;
}

export async function importOfxTransactions(payload: OfxImportPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/finance/statements/import-ofx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error?.message ?? body.error ?? `Falha na importação (${res.status})`);
  }
}

export function toOfxImportPayload(
  rows: ParsedStatementTransaction[],
  opts: { cdConta: number; cdFilial: number; opcaoImportacao: string },
): OfxImportPayload {
  const datas = rows.map((r) => r.data).filter(Boolean).sort();
  return {
    cdConta: opts.cdConta,
    cdFilial: opts.cdFilial,
    dataInicial: datas[0] ?? new Date().toISOString().slice(0, 10),
    opcaoImportacao: opts.opcaoImportacao,
    transacoes: rows.map((r) => ({
      valor: r.valor,
      data: r.data,
      descricao: r.descricao,
      tipo: r.tipo,
    })),
  };
}
