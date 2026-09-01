import { CopilotAnswer, SpecialistId } from "../types/copilot";
import { normalizeCopilotAnswer } from "./copilot-normalizer";

export interface HttpCopilotQueryOptions {
  question: string;
  specialist: SpecialistId;
  unidades: number[];
  startDate: string;
  endDate: string;
  signal?: AbortSignal;
}

export interface DateCoverageResponse {
  units: number[];
  firstCompleteDate: string | null;
  lastCompleteDate: string | null;
  suggestedStartDate: string | null;
  suggestedEndDate: string | null;
  gaps?: unknown[];
  empty?: boolean;
  source?: string;
  webpostoWrites?: number;
  blocked?: { code: string; message: string } | null;
}

export class HttpCopilotError extends Error {
  status: number;
  detail: string;

  constructor(message: string, status: number, detail: string) {
    super(message);
    this.name = "HttpCopilotError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Adaptador HTTP exclusivo para o Copiloto Executivo.
 * Operação 100% via backend real/local (sem fallback para dados simulados).
 */
export async function queryHttpCopilot(options: HttpCopilotQueryOptions): Promise<CopilotAnswer> {
  const { question, specialist, unidades, startDate, endDate, signal } = options;

  const payload = {
    pergunta: question,
    especialista: specialist,
    unidades,
    periodo: {
      inicio: startDate,
      fim: endDate,
    },
  };

  const response = await fetch("/api/proxy/executive-copilot/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    const status = response.status;
    let customMessage = `Erro de resposta HTTP ${status} ao consultar Copiloto Backend.`;

    if (status === 401) {
      customMessage = "Sua sessão expirou";
    } else if (status === 403) {
      customMessage = "Você não possui acesso a esta unidade";
    } else if (status === 422) {
      customMessage = "Revise os filtros ou a pergunta";
    } else if (status === 503) {
      customMessage = "Backend local indisponível";
    }

    throw new HttpCopilotError(customMessage, status, errorText);
  }

  const rawJson = await response.json();
  return normalizeCopilotAnswer(rawJson);
}

/**
 * Consome GET /api/proxy/executive-copilot/coverage?unidades=... para obter cobertura de datas do backend.
 * Sem fallbacks de datas hardcoded.
 */
export async function fetchCopilotDateCoverage(
  unidades: number[],
  signal?: AbortSignal
): Promise<DateCoverageResponse> {
  const params = new URLSearchParams();
  if (Array.isArray(unidades)) {
    unidades.forEach((u) => params.append("unidades", String(u)));
  }

  const queryString = params.toString();
  const endpoint = `/api/proxy/executive-copilot/coverage${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(endpoint, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    signal,
  });

  if (!response.ok) {
    const status = response.status;
    let customMessage = `Erro HTTP ${status} ao consultar cobertura de datas.`;
    if (status === 401) {
      customMessage = "Sua sessão expirou. Entre novamente para consultar a cobertura.";
    } else if (status === 403) {
      customMessage = "Você não possui acesso à cobertura desta unidade.";
    } else {
      customMessage = "Não foi possível consultar a cobertura agora.";
    }
    const err = new Error(customMessage);
    (err as any).status = status;
    throw err;
  }

  const data = await response.json();
  return {
    units: Array.isArray(data.units) ? data.units : (unidades || []),
    firstCompleteDate: data.firstCompleteDate ?? null,
    lastCompleteDate: data.lastCompleteDate ?? null,
    suggestedStartDate: data.suggestedStartDate ?? null,
    suggestedEndDate: data.suggestedEndDate ?? null,
    gaps: Array.isArray(data.gaps) ? data.gaps : [],
    empty: Boolean(data.empty ?? (!data.suggestedStartDate || !data.suggestedEndDate)),
    source: data.source ?? "webposto_api",
    webpostoWrites: typeof data.webpostoWrites === "number" ? data.webpostoWrites : 0,
    blocked: data.blocked ?? null,
  };
}

/**
 * Consome GET /api/proxy/health apenas para verificar disponibilidade do backend.
 */
export async function fetchCopilotHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch("/api/proxy/health?demo=copilot", {
      method: "GET",
      credentials: "include",
      signal,
    });
    return response.ok;
  } catch {
    return false;
  }
}
