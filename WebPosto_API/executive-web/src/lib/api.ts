/**
 * Serviço de API — Sprint 51.
 */

import {
  DashboardBundle,
  SimulationInput,
  SimulationResult,
  DreLine,
  ReviewableFact,
  ExecutiveReport,
  InventoryPredictionResponse,
  SalesCompositionResponse,
  DataAuditResponse,
  ExpenseDetailsResponse,
  CardFraudAuditResponse,
  AuditFraudSettings,
  CashierAuditAdjustPayload,
  CashierAuditFechamento,
  CashierAuditResponse,
  PistaLiveResponse,
  LiveFeedResponse,
  PistaIntelligenceResponse,
  UnitsPerformanceResponse,
  UnitsPerformanceDetailResponse,
  RushHeatmapResponse,
  ForecourtLayout,
  ForecourtPosition,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";
const API_PREFIX = "/api/proxy";

function networkErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err || "");
  if (/Failed to fetch|NetworkError|Load failed|fetch failed/i.test(msg)) {
    return "Falha de rede ao falar com a API (proxy/backend). Confirme API :8040 e Next :3000.";
  }
  if (/aborted|timeout|TimeoutError/i.test(msg)) {
    return "Tempo esgotado na consulta à API — tente novamente.";
  }
  return msg || "Erro desconhecido na API";
}

async function browserFetch(url: string, options: RequestInit = {}): Promise<Response> {
  try {
    const { timeoutMs, ...rest } = options as RequestInit & { timeoutMs?: number };
    const signal =
      rest.signal ??
      (typeof timeoutMs === "number" && timeoutMs > 0
        ? AbortSignal.timeout(timeoutMs)
        : undefined);
    return await fetch(url, {
      ...rest,
      signal,
      headers: {
        "Content-Type": "application/json",
        ...rest.headers,
      },
    });
  } catch (err) {
    throw new Error(networkErrorMessage(err));
  }
}

const OFFLINE_ERROR = "Serviço temporariamente indisponível";

export class OfflineSourceUnavailableError extends Error {
  code = "OFFLINE_SOURCE_UNAVAILABLE";
  constructor(message?: string) {
    super(message || "Modo local offline — fonte indisponível");
    this.name = "OfflineSourceUnavailableError";
  }
}

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const proxyEndpoint = endpoint.startsWith("/api/v1/") 
    ? `${API_PREFIX}${endpoint.replace("/api/v1/", "/")}`
    : endpoint;

  const url = `${API_BASE_URL}${proxyEndpoint}`;
  const response = await browserFetch(url, options);

  const contentType = response.headers.get("content-type");
  const isJson = !!contentType && contentType.includes("application/json");

  // Sprint 03: 502/503 → envelope offline sem throw não tratado no React
  if (response.status === 502 || response.status === 503) {
    if (isJson) {
      const body = await response.json() as {
        success?: boolean;
        data?: unknown;
        error?: string;
        code?: string;
        message?: string;
        offlineMode?: boolean;
      };
      if (body?.code === "OFFLINE_SOURCE_UNAVAILABLE" || body?.data == null && body?.offlineMode) {
        throw new OfflineSourceUnavailableError(body.message || body.error);
      }
      if (body?.data != null) return body.data;
    }
    throw new Error(OFFLINE_ERROR);
  }

  if (!response.ok) {
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    if (isJson) {
      try {
        const errorData = (await response.json()) as {
          error?: string;
          message?: string;
          detail?: string | { message?: string; code?: string };
        };
        const detail =
          typeof errorData.detail === "string"
            ? errorData.detail
            : errorData.detail?.message;
        errorMessage = detail || errorData.error || errorData.message || errorMessage;
      } catch {
        // Not JSON, use default status text
      }
    }
    throw new Error(errorMessage);
  }

  if (!isJson) {
    throw new Error("Resposta da API não é um JSON válido");
  }

  const result = await response.json() as { success: boolean; data: unknown; error?: string };
  if (!result.success) {
    throw new Error(result.error || "Unknown API error");
  }

  return result.data;
}

async function fetchDirectApi(endpoint: string, options: RequestInit = {}) {
  const proxyEndpoint = endpoint.startsWith("/api/v1/")
    ? `${API_PREFIX}${endpoint.replace("/api/v1/", "/")}`
    : endpoint;

  const url = `${API_BASE_URL}${proxyEndpoint}`;
  const response = await browserFetch(url, options);

  const contentType = response.headers.get("content-type");
  const isJson = !!contentType && contentType.includes("application/json");

  // Sprint 03: backend offline — devolve envelope padrão (sem throw)
  if (response.status === 502 || response.status === 503) {
    if (isJson) {
      try {
        return await response.json();
      } catch {
        // fall through
      }
    }
    return { success: false, error: OFFLINE_ERROR, data: null, offline: true };
  }

  if (!response.ok) {
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    if (isJson) {
      try {
        const errorData = (await response.json()) as {
          error?: string;
          message?: string;
          detail?: string | { message?: string; code?: string };
        };
        const detail =
          typeof errorData.detail === "string"
            ? errorData.detail
            : errorData.detail?.message;
        errorMessage = detail || errorData.error || errorData.message || errorMessage;
      } catch {
        // Not JSON, use default status text
      }
    }
    throw new Error(errorMessage);
  }

  if (!isJson) {
    throw new Error("Resposta da API não é um JSON válido");
  }

  return response.json();
}

export type PostosInteligenciaResponse = {
  success: boolean;
  webpostoWrites?: number;
  periodo?: { inicio: string; fim: string };
  unidades: Array<Record<string, unknown>>;
  comparacao?: Array<Record<string, unknown>>;
  recomendacoes?: Array<Record<string, unknown>>;
  avisos?: string[];
  trafegoDisponivel?: boolean;
};

export const apiService = {
  async getDashboardBundle(start: string, end: string, company?: number): Promise<DashboardBundle> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    return fetchApi(`/api/v1/executive/dashboard/bundle?${params}`) as Promise<DashboardBundle>;
  },

  async simulateMarginImpact(input: SimulationInput): Promise<SimulationResult> {
    return fetchApi(`/api/v1/executive/simulate-margin-impact`, {
      method: "POST",
      body: JSON.stringify(input),
    }) as Promise<SimulationResult>;
  },

  async resolveAlert(alertId: number, notes?: string): Promise<void> {
    const params = notes ? `?notes=${encodeURIComponent(notes)}` : "";
    return fetchApi(`/api/v1/executive/alerts/${alertId}/resolve${params}`, {
      method: "PATCH",
    }) as Promise<void>;
  },

  async getAlertHistory(start?: string, end?: string, company?: number): Promise<unknown[]> {
    const params = new URLSearchParams();
    if (start) params.append("dataInicial", start);
    if (end) params.append("dataFinal", end);
    if (company) params.append("empresaCodigo", company.toString());
    return fetchApi(`/api/v1/executive/alerts/history?${params}`) as Promise<unknown[]>;
  },

  async getCompleteDre(
    start: string,
    end: string,
    company?: number,
    opts?: { refresh?: boolean; timeoutMs?: number; regime?: string }
  ): Promise<{ lines: DreLine[]; fromCache?: boolean; stale?: boolean }> {
    const regime = opts?.regime || "competencia";
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      summary: "true",
      regime,
    });
    if (company) params.append("empresaCodigo", company.toString());
    if (opts?.refresh) params.append("refresh", "true");
    const cacheKey = `dre-summary:${start}:${end}:${company ?? "network"}:${regime}`;

    const mapLines = (data: { lines?: Array<Record<string, unknown>> }): DreLine[] =>
      (data?.lines || []).map((row) => {
        const n = (v: unknown) => {
          const x = Number(v);
          return Number.isFinite(x) ? x : 0;
        };
        const dept = String(row.department || "outros");
        const department = (
          ["combustiveis", "conveniencia", "lubrificantes", "outros"].includes(dept)
            ? dept
            : "outros"
        ) as DreLine["department"];
        const released = String(row.status || "").toUpperCase() === "LIBERADO";
        return {
          companyName: String(row.companyName || ""),
          department,
          revenue: n(row.revenue),
          cost: n(row.cost),
          grossMargin: n(row.grossMargin),
          expenses: n(row.expenses),
          operatingResult: n(row.operatingResult),
          operatingMarginPct: n(row.operatingMarginPct),
          status: released ? "ESTAVEL" : "ALERTA",
        };
      });

    try {
      const data = (await fetchApi(
        `/api/v1/finance/director-reconciliation/dre-complete?${params}`,
        { timeoutMs: opts?.timeoutMs ?? 12000 } as RequestInit
      )) as { lines?: Array<Record<string, unknown>> };
      const lines = mapLines(data);
      try {
        sessionStorage.setItem(
          cacheKey,
          JSON.stringify({ ts: Date.now(), lines })
        );
      } catch {
        /* ignore quota */
      }
      return { lines };
    } catch {
      try {
        const raw = sessionStorage.getItem(cacheKey);
        if (raw) {
          const parsed = JSON.parse(raw) as { lines?: DreLine[] };
          if (Array.isArray(parsed?.lines) && parsed.lines.length) {
            return { lines: parsed.lines, fromCache: true, stale: true };
          }
        }
      } catch {
        /* ignore */
      }
      return { lines: [] };
    }
  },

  async getReviewableFacts(start: string, end: string, company?: number): Promise<ReviewableFact[]> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      const data = (await fetchApi(
        `/api/v1/finance/director-reconciliation?${params}`
      )) as { reviewableFacts?: ReviewableFact[] };
      return Array.isArray(data?.reviewableFacts) ? data.reviewableFacts : [];
    } catch {
      return [];
    }
  },

  async classifyExpense(factId: string, department: string, reviewer: string, rationale: string): Promise<void> {
    return fetchApi(`/api/v1/finance/director-reconciliation/review`, {
      method: "POST",
      body: JSON.stringify({ factId, department, reviewer, rationale }),
    }) as Promise<void>;
  },

  async getSalesAnalytics(start: string, end: string, company?: number): Promise<unknown> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    return fetchApi(`/api/v1/executive/sales/analytics?${params}`);
  },

  async getPistaRushHeatmap(
    company?: number,
    window?: { inicio?: string; fim?: string }
  ): Promise<RushHeatmapResponse> {
    const params = new URLSearchParams();
    if (company) params.set("empresaCodigo", company.toString());
    // datetime-local → ISO (YYYY-MM-DDTHH:mm)
    if (window?.inicio) params.set("dataInicial", window.inicio);
    if (window?.fim) params.set("dataFinal", window.fim);
    const empty: RushHeatmapResponse = {
      success: false,
      posts: [],
      intelligence_cards: [],
    };
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/pista-rush-heatmap?${params}`
      )) as { data?: RushHeatmapResponse } & RushHeatmapResponse;
      if (envelope?.data?.posts) return envelope.data;
      if (envelope?.posts) return envelope as RushHeatmapResponse;
      return empty;
    } catch {
      return empty;
    }
  },

  async postPistaIntervention(body: {
    empresa_codigo?: number;
    unidade_id?: number;
    tipo?: string;
    suspeita_type?: string;
    subject_id?: string;
    acao?: string;
    operador?: string;
    metrics_baseline?: Record<string, unknown>;
  }): Promise<unknown> {
    return fetchDirectApi(`/api/v1/executive/pista-interventions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  async getForecourtActiveLayout(stationId: number): Promise<ForecourtLayout | null> {
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/forecourt-layout/active?stationId=${stationId}`
      )) as { success?: boolean; data?: ForecourtLayout };
      return envelope?.data ?? null;
    } catch {
      return null;
    }
  },

  async updateForecourtLayout(
    layoutId: string,
    body: { positions?: ForecourtPosition[]; islands?: ForecourtLayout["islands"]; mapping_status?: string }
  ): Promise<ForecourtLayout> {
    const envelope = (await fetchDirectApi(
      `/api/v1/executive/forecourt-layout/${layoutId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    )) as { data?: ForecourtLayout } & ForecourtLayout;
    return (envelope.data || envelope) as ForecourtLayout;
  },

  async seedForecourtCasaCaiada(force = false): Promise<ForecourtLayout & { seeded?: boolean; seed_id?: string }> {
    const envelope = (await fetchDirectApi(
      `/api/v1/executive/forecourt-layout/seed/casa-caiada?force=${force ? "true" : "false"}`,
      { method: "POST" }
    )) as { data?: ForecourtLayout & { seeded?: boolean; seed_id?: string } };
    return (envelope.data || {}) as ForecourtLayout & { seeded?: boolean; seed_id?: string };
  },

  async seedForecourtPostoReal(force = false): Promise<ForecourtLayout & { seeded?: boolean; seed_id?: string }> {
    const envelope = (await fetchDirectApi(
      `/api/v1/executive/forecourt-layout/seed/posto-real?force=${force ? "true" : "false"}`,
      { method: "POST" }
    )) as { data?: ForecourtLayout & { seeded?: boolean; seed_id?: string } };
    return (envelope.data || {}) as ForecourtLayout & { seeded?: boolean; seed_id?: string };
  },

  async getUnitsPerformance(
    start: string,
    end: string
  ): Promise<UnitsPerformanceResponse> {
    const params = new URLSearchParams({
      data_inicio: start,
      data_fim: end,
    });
    const empty: UnitsPerformanceResponse = {
      success: false,
      periodo: { inicio: start, fim: end },
      rede: {
        faturamento_total_rs: 0,
        despesas_totais_rs: 0,
        lucro_liquido_global_rs: 0,
        resultado_operacional_rs: 0,
        margem_media_pct: 0,
        galonagem_total_litros: 0,
      },
      unidades: [],
      insights: [],
    };
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/units-performance?${params}`
      )) as { data?: UnitsPerformanceResponse } & UnitsPerformanceResponse;
      if (envelope?.data?.unidades) return envelope.data;
      if (envelope?.unidades) return envelope as UnitsPerformanceResponse;
      return empty;
    } catch {
      return empty;
    }
  },

  async getUnitPerformanceDetail(
    unidadeId: number,
    start: string,
    end: string
  ): Promise<UnitsPerformanceDetailResponse> {
    const params = new URLSearchParams({
      data_inicio: start,
      data_fim: end,
    });
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/units-performance/${unidadeId}?${params}`
      )) as { data?: UnitsPerformanceDetailResponse } & UnitsPerformanceDetailResponse;
      if (envelope?.data?.unidade) return envelope.data;
      if (envelope?.unidade) return envelope as UnitsPerformanceDetailResponse;
      throw new Error("Detalhe da unidade indisponível");
    } catch (err) {
      return {
        success: false,
        periodo: { inicio: start, fim: end },
        unidade: {
          unidade_id: unidadeId,
          nome_unidade: `Unidade ${unidadeId}`,
          galonagem_litros: 0,
          faturamento_total_rs: 0,
          despesas_totais_rs: 0,
          diferenca_lucro_rs: 0,
          resultado_operacional_rs: 0,
          margem_percentual: 0,
          margem_operacional_pct: 0,
          status_operacional: "CRITICO",
          folha_pagamento_rs: 0,
        },
        evolucao_mensal: [],
        despesas_por_categoria: [],
        mensagem: err instanceof Error ? err.message : "Erro ao carregar unidade",
      };
    }
  },

  async getDreIntelligence(
    start: string,
    end: string,
    opts?: {
      regime?: string;
      compare?: "m1" | "y1" | "t3" | "t6" | "t12";
      horizon?: "mes" | "trimestre" | "ano";
      company?: number;
    }
  ): Promise<import("@/types/api").DreIntelligenceResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      regime: opts?.regime || "competencia",
      compare: opts?.compare || "m1",
      horizon: opts?.horizon || "mes",
    });
    if (opts?.company) params.append("empresaCodigo", String(opts.company));
    return (await fetchApi(
      `/api/v1/executive/dre-intelligence?${params}`
    )) as import("@/types/api").DreIntelligenceResponse;
  },

  async getDreMultidimensional(
    start: string,
    end: string,
    opts?: { regime?: string; company?: number }
  ): Promise<import("@/types/api").DreMultidimensionalResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      regime: opts?.regime || "competencia",
    });
    if (opts?.company) params.append("empresaCodigo", String(opts.company));
    return (await fetchApi(
      `/api/v1/executive/dre-multidimensional?${params}`
    )) as import("@/types/api").DreMultidimensionalResponse;
  },

  async getHealthSynthesis(
    start: string,
    end: string,
    opts?: {
      regime?: string;
      compare?: "m1" | "y1" | "t3" | "t6" | "t12";
      company?: number;
    }
  ): Promise<import("@/types/api").ExecutiveHealthSynthesisResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      regime: opts?.regime || "competencia",
      compare: opts?.compare || "m1",
    });
    if (opts?.company) params.append("empresaCodigo", String(opts.company));
    return (await fetchApi(
      `/api/v1/executive/health-synthesis?${params}`
    )) as import("@/types/api").ExecutiveHealthSynthesisResponse;
  },

  async getBranchBenchmark(
    start: string,
    end: string,
    opts?: {
      regime?: string;
      compare?: "m1" | "y1" | "t3" | "t6" | "t12";
      companies?: number[];
    }
  ): Promise<import("@/types/api").BranchBenchmarkResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      regime: opts?.regime || "competencia",
      compare: opts?.compare || "m1",
    });
    for (const code of opts?.companies || []) {
      params.append("empresaCodigo", String(code));
    }
    return (await fetchApi(
      `/api/v1/executive/branch-benchmark?${params}`
    )) as import("@/types/api").BranchBenchmarkResponse;
  },

  async getDataAudit(
    start: string,
    end: string,
    company?: number,
    opts?: { regime?: string }
  ): Promise<DataAuditResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      regime: opts?.regime || "competencia",
    });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchApi(`/api/v1/executive/data-audit?${params}`)) as DataAuditResponse;
    } catch (err) {
      if (err instanceof OfflineSourceUnavailableError) {
        return {
          periodo: { inicio: start, fim: end },
          filiais: [],
          consolidado: {},
          success: false,
          unavailable: true,
          mensagem: err.message,
          regime: opts?.regime || "competencia",
        };
      }
      return {
        periodo: { inicio: start, fim: end },
        filiais: [],
        consolidado: {},
        success: false,
        mensagem: "Fallback local — data-audit indisponível",
        regime: opts?.regime || "competencia",
      };
    }
  },

  async adjustCashierAudit(
    fechamentoId: string,
    body: CashierAuditAdjustPayload
  ): Promise<CashierAuditFechamento> {
    const envelope = (await fetchDirectApi(
      `/api/v1/finance/cashier-audit/${encodeURIComponent(fechamentoId)}/adjust`,
      {
        method: "PATCH",
        body: JSON.stringify(body),
      }
    )) as { success?: boolean; data?: CashierAuditFechamento; error?: string };
    if (!envelope?.data?.id) {
      throw new Error(envelope?.error || "Falha ao ajustar fechamento de caixa");
    }
    return envelope.data;
  },

  async getCashierAudit(
    company?: number,
    pagina: number = 1,
    limite: number = 20
  ): Promise<CashierAuditResponse> {
    const params = new URLSearchParams({
      pagina: String(pagina),
      limite: String(limite),
    });
    if (company) params.append("empresaCodigo", company.toString());
    const empty: CashierAuditResponse = {
      success: false,
      fromCache: true,
      resumoDia: {
        totalEsperado: 0,
        totalDeclarado: 0,
        divergenciaTotal: 0,
        sobras: 0,
        faltas: 0,
      },
      fechamentosPorTurno: [],
      quebrasPorFormaPagamento: [],
      totalFechamentos: 0,
      hasMore: false,
      observacoes: ["Cache de auditoria de caixas indisponível"],
    };
    try {
      // fetchDirectApi: envelope completo { success, data } — evita unwrap ambíguo
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/audit/cashier?${params}`
      )) as { success?: boolean; data?: CashierAuditResponse; error?: string } & CashierAuditResponse;

      if (envelope?.data?.resumoDia) return envelope.data;
      if (envelope?.resumoDia) return envelope as CashierAuditResponse;
      if (envelope?.success === false) {
        throw new Error(envelope.error || "Auditoria de caixas indisponível");
      }
      return empty;
    } catch {
      return empty;
    }
  },

  async getCardFraudAudit(
    start: string,
    end: string,
    company?: number,
    limiarRetencaoMinutos?: number | null,
    filtros?: {
      frentista_id?: number | null;
      frentista_nome?: string;
      tipo_infracao?: string;
      tempo_retencao_min?: number | null;
      forma_pagamento?: string;
      busca_texto?: string;
      filial_id?: number | null;
    }
  ): Promise<CardFraudAuditResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
    });
    // Sem limiar → engine usa settings salvos (thresholds dinâmicos)
    if (limiarRetencaoMinutos != null) {
      params.set("limiarRetencaoMinutos", String(limiarRetencaoMinutos));
    }
    if (company) params.append("empresaCodigo", company.toString());
    if (filtros?.filial_id != null) params.set("filial_id", String(filtros.filial_id));
    if (filtros?.frentista_id != null) params.set("frentista_id", String(filtros.frentista_id));
    if (filtros?.frentista_nome) params.set("frentista_nome", filtros.frentista_nome);
    if (filtros?.tipo_infracao) params.set("tipo_infracao", filtros.tipo_infracao);
    if (filtros?.tempo_retencao_min != null) {
      params.set("tempo_retencao_min", String(filtros.tempo_retencao_min));
    }
    if (filtros?.forma_pagamento) params.set("forma_pagamento", filtros.forma_pagamento);
    if (filtros?.busca_texto) params.set("busca_texto", filtros.busca_texto);
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/audit/card-fraud?${params}`
      )) as { success?: boolean; data?: CardFraudAuditResponse } & CardFraudAuditResponse;
      const payload =
        envelope?.data && (envelope.data.resumo || envelope.data.resumoExecutivo || envelope.data.ocorrencias)
          ? envelope.data
          : envelope;
      return {
        ...payload,
        success: payload.success !== false,
        fromCache: true,
        resumo: payload.resumo || payload.resumoExecutivo || payload.resumo,
        resumoExecutivo: payload.resumoExecutivo || payload.resumo,
      } as CardFraudAuditResponse;
    } catch {
      return {
        success: false,
        synthetic: false,
        fonte: "FraudDetectionEngine",
        endpoint: "/api/v1/abastecimentos/baixados",
        periodo: { inicio: start, fim: end },
        empresaCodigo: company ?? null,
        limiarRetencaoMinutos: limiarRetencaoMinutos ?? 15,
        limiarCriticoMinutos: 30,
        resumo: {
          totalAgrupamentosSuspeitos: 0,
          totalCriticos: 0,
          totalAtencao: 0,
          valorTotalRetidoCartoes: 0,
          valorCritico: 0,
          frentistaMaiorIncidencia: "SEM REGISTRO NO PERIODO",
          frentistaMaiorIncidenciaQtd: 0,
          abastecimentosCriticosBanner: 0,
        },
        ocorrencias: [],
        bannerAlerta: null,
        observacoes: ["Lista vazia — backend indisponível (synthetic: false)"],
      };
    }
  },

  async getPistaLive(company?: number): Promise<PistaLiveResponse> {
    const params = new URLSearchParams();
    if (company) params.set("empresaCodigo", company.toString());
    const empty: PistaLiveResponse = {
      success: false,
      totalBicos: 0,
      totalRetencoes: 0,
      filiais: [],
      observacoes: ["Cache de pista ao vivo indisponível"],
    };
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/audit/pista-live?${params}`
      )) as { success?: boolean; data?: PistaLiveResponse } & PistaLiveResponse;
      if (envelope?.data?.filiais) return envelope.data;
      if (envelope?.filiais) return envelope as PistaLiveResponse;
      return empty;
    } catch {
      return empty;
    }
  },

  async getLiveFeed(
    company?: number | null,
    ordenarPor: "faturamento" | "volume" = "faturamento",
    streamLimit = 60
  ): Promise<LiveFeedResponse> {
    const params = new URLSearchParams({
      ordenarPor,
      streamLimit: String(streamLimit),
    });
    if (company) params.set("empresaCodigo", String(company));
    const empty: LiveFeedResponse = {
      success: false,
      kpis: {
        faturamento_dia: 0,
        volume_litros: 0,
        qtd_abastecimentos: 0,
        ticket_medio_pista: 0,
        mix_aditivada_pct: 0,
        ritmo_abast_por_minuto: 0,
      },
      ranking: [],
      destaques: {
        campeao_aditivada: null,
        oportunidade_treinamento: null,
        media_pct_aditivada: 0,
      },
      stream: [],
      observacoes: ["Live feed indisponível"],
    };
    try {
      const data = (await fetchDirectApi(
        `/api/v1/executive/live-feed?${params}`
      )) as LiveFeedResponse;
      if (!data?.kpis) return empty;
      return data;
    } catch {
      return empty;
    }
  },

  async getPistaIntelligence(
    company?: number | null,
    opts?: { frentistaId?: number | null; frentistaNome?: string | null }
  ): Promise<PistaIntelligenceResponse> {
    const params = new URLSearchParams();
    if (company) params.set("empresaCodigo", String(company));
    if (opts?.frentistaId != null) {
      params.set("frentistaId", String(opts.frentistaId));
    }
    if (opts?.frentistaNome) {
      params.set("frentistaNome", opts.frentistaNome);
    }
    const empty: PistaIntelligenceResponse = {
      success: false,
      tbico: {
        media_min: 0,
        media_segundos: 0,
        status: "IDEAL",
        cor: "verde",
        amostra: 0,
        limites: { verde_max: 2.5, amarelo_max: 4.5 },
        ponteiro_pct: 0,
      },
      frentistas: [],
      destaque_rush: null,
      duelo: {
        faturamento_hoje: 0,
        faturamento_ontem: 0,
        delta_faturamento: 0,
        litros_hoje: 0,
        litros_ontem: 0,
        delta_litros: 0,
        qtd_hoje: 0,
        qtd_ontem: 0,
        vencedor: "EMPATE",
        label_delta_fat: "R$ 0,00",
        label_delta_litros: "0 L",
      },
      alertas: [],
    };
    try {
      const q = params.toString();
      const data = (await fetchDirectApi(
        `/api/v1/executive/pista-intelligence${q ? `?${q}` : ""}`
      )) as PistaIntelligenceResponse;
      if (!data?.tbico) return empty;
      return data;
    } catch {
      return empty;
    }
  },

  async getAuditFraudSettings(empresaId: number = 0): Promise<AuditFraudSettings> {
    const raw = (await fetchApi(
      `/api/v1/executive/audit/settings?empresaId=${empresaId}`
    )) as { data?: AuditFraudSettings } & AuditFraudSettings;
    return (raw?.data || raw) as AuditFraudSettings;
  },

  async saveAuditFraudSettings(
    body: Partial<AuditFraudSettings> & {
      tempo_retencao_critico_min: number;
      tempo_retencao_atencao_min: number;
    }
  ): Promise<AuditFraudSettings> {
    const raw = (await fetchApi(`/api/v1/executive/audit/settings`, {
      method: "PUT",
      body: JSON.stringify({
        empresa_id: body.empresa_id ?? 0,
        tempo_retencao_critico_min: body.tempo_retencao_critico_min,
        tempo_retencao_atencao_min: body.tempo_retencao_atencao_min,
        tempo_agrupamento_max_min: body.tempo_agrupamento_max_min ?? 15,
        percentual_desconto_suspeito_pct: body.percentual_desconto_suspeito_pct ?? 10,
        recorrencia_cpf_cartao_limite: body.recorrencia_cpf_cartao_limite ?? 3,
      }),
    })) as { data?: AuditFraudSettings } & AuditFraudSettings;
    return (raw?.data || raw) as AuditFraudSettings;
  },

  async getExpenseDetails(
    start: string,
    end: string,
    categoriaPlanoContas: string,
    company?: number
  ): Promise<ExpenseDetailsResponse> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
      categoria: categoriaPlanoContas,
      categoriaPlanoContas,
    });
    if (company) params.append("empresaCodigo", company.toString());
    const empty = (msg: string): ExpenseDetailsResponse => ({
      empresaCodigo: company ?? null,
      periodo: { inicio: start, fim: end },
      categoria: categoriaPlanoContas,
      categoriaKey: categoriaPlanoContas,
      subtotal: 0,
      quantidade: 0,
      itens: [],
      success: false,
      mensagem: msg,
    });
    try {
      // Preferência: drill-down lazy finance (conta específica sob demanda)
      return (await fetchApi(
        `/api/v1/finance/expense-entry/drill-down?${params}`,
        { timeoutMs: 15000 } as RequestInit
      )) as ExpenseDetailsResponse;
    } catch {
      try {
        return (await fetchApi(
          `/api/v1/executive/expenses/details?${params}`,
          { timeoutMs: 15000 } as RequestInit
        )) as ExpenseDetailsResponse;
      } catch (err) {
        return empty(err instanceof Error ? err.message : "Falha ao carregar detalhes");
      }
    }
  },

  async getPlanoContasOptions(): Promise<
    Array<{ codigo: number; nome: string; label: string; hierarquia?: string; categoria?: string }>
  > {
    try {
      const data = (await fetchApi(`/api/v1/executive/plano-contas`)) as {
        itens?: Array<{
          codigo: number;
          nome: string;
          label: string;
          hierarquia?: string;
          categoria?: string;
        }>;
      };
      return data?.itens || [];
    } catch {
      return [];
    }
  },

  async reclassifyExpenseEntry(
    lancamentoId: string,
    novoPlanoCodigo: string | number,
    motivo = "Reclassificação via DRE Executiva",
    planoAnteriorCodigo?: number | null
  ): Promise<{
    success: boolean;
    lancamento_id?: string;
    novo_plano_codigo?: number;
    plano_label?: string;
    plano_nome?: string;
    categoria?: string;
    error?: string;
  }> {
    try {
      const data = (await fetchApi(
        `/api/v1/finance/expense-entry/${encodeURIComponent(lancamentoId)}/reclassify`,
        {
          method: "PATCH",
          body: JSON.stringify({
            novo_plano_codigo: novoPlanoCodigo,
            motivo,
            plano_anterior_codigo: planoAnteriorCodigo ?? null,
          }),
        }
      )) as {
        lancamento_id?: string;
        novo_plano_codigo?: number;
        plano_label?: string;
        plano_nome?: string;
        categoria?: string;
      };
      return { success: true, ...data };
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : "Falha na reclassificação",
      };
    }
  },

  async getElasticityProducts(
    company?: number,
    days = 90
  ): Promise<{ produtos: unknown[]; mensagem?: string | null }> {
    const params = new URLSearchParams({ days: String(days) });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchApi(
        `/api/v1/executive/sales/elasticity-products?${params}`
      )) as { produtos: unknown[]; mensagem?: string | null };
    } catch {
      return { produtos: [], mensagem: "Histórico local indisponível" };
    }
  },

  async simulateElasticity(
    company: number,
    codigoProduto: string,
    deltaPrecoRs: number,
    days = 90
  ): Promise<{ success?: boolean; projecao?: unknown; mensagem?: string }> {
    const params = new URLSearchParams({
      empresaCodigo: String(company),
      codigoProduto,
      deltaPrecoRs: String(deltaPrecoRs),
      days: String(days),
    });
    try {
      return (await fetchApi(
        `/api/v1/executive/sales/elasticity-simulate?${params}`
      )) as { success?: boolean; projecao?: unknown; mensagem?: string };
    } catch (err) {
      return {
        success: false,
        mensagem: err instanceof Error ? err.message : "Falha na simulação",
      };
    }
  },

  async getSalesComposition(start: string, end: string, company?: number): Promise<SalesCompositionResponse> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchApi(
        `/api/v1/executive/sales/composition?${params}`
      )) as SalesCompositionResponse;
    } catch (err) {
      if (err instanceof OfflineSourceUnavailableError) {
        return {
          summary: {
            faturamentoTotal: 0,
            faturamentoCombustivel: 0,
            faturamentoProdutosPista: 0,
            faturamentoConveniencia: 0,
            litrosVendidos: 0,
            quantidadeAbastecimentos: 0,
            clientesLoja: 0,
            ticketMedioAbastecimento: 0,
            receitaNaoCombustivelPorAbastecimento: 0,
            litrosPorAbastecimento: 0,
            penetracaoProdutosPistaPercentual: 0,
            penetracaoConvenienciaPercentual: 0,
            penetracaoCrossSellingPercentual: 0,
          },
          compositionBySector: [],
          crossSellingFunnel: {
            totalAbastecimentos: 0,
            clientesLoja: 0,
            transacoesCombustivelProdutoPista: 0,
            transacoesCombustivelConveniencia: 0,
            transacoesCombustivelComboTotal: 0,
            penetracaoProdutosPistaPercentual: 0,
            penetracaoConvenienciaPercentual: 0,
            penetracaoTotalPercentual: 0,
            relacaoLojaPistaPercentual: 0,
          },
          combustiveis: [],
          produtosPista: [],
          conveniencia: [],
          fallback: true,
          unavailable: true,
          mensagem: err.message,
        };
      }
      return {
        summary: {
          faturamentoTotal: 0,
          faturamentoCombustivel: 0,
          faturamentoProdutosPista: 0,
          faturamentoConveniencia: 0,
          litrosVendidos: 0,
          quantidadeAbastecimentos: 0,
          clientesLoja: 0,
          ticketMedioAbastecimento: 0,
          receitaNaoCombustivelPorAbastecimento: 0,
          litrosPorAbastecimento: 0,
          penetracaoProdutosPistaPercentual: 0,
          penetracaoConvenienciaPercentual: 0,
          penetracaoCrossSellingPercentual: 0,
        },
        compositionBySector: [],
        crossSellingFunnel: {
          totalAbastecimentos: 0,
          clientesLoja: 0,
          transacoesCombustivelProdutoPista: 0,
          transacoesCombustivelConveniencia: 0,
          transacoesCombustivelComboTotal: 0,
          penetracaoProdutosPistaPercentual: 0,
          penetracaoConvenienciaPercentual: 0,
          penetracaoTotalPercentual: 0,
          relacaoLojaPistaPercentual: 0,
        },
        combustiveis: [],
        produtosPista: [],
        conveniencia: [],
        fallback: true,
        mensagem: "Fallback local — composition indisponível",
      };
    }
  },

  async getLogisticsEfficiency(start: string, end: string, company?: number): Promise<unknown> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    return fetchApi(`/api/v1/executive/logistics/efficiency?${params}`);
  },

  async getTreasuryConsolidation(company?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (company) params.append("empresaCodigo", company.toString());
    return fetchApi(`/api/v1/executive/treasury/consolidation?${params}`);
  },

  async getExecutiveConsolidatedReport(
    start?: string,
    end?: string,
    company?: number
  ): Promise<ExecutiveReport> {
    const params = new URLSearchParams();
    if (start) params.append("dataInicial", start);
    if (end) params.append("dataFinal", end);
    if (company) params.append("empresaCodigo", company.toString());
    const query = params.toString() ? `?${params}` : "";
    return fetchDirectApi(`/api/v1/executive/consolidated-report${query}`) as Promise<ExecutiveReport>;
  },

  /** DRE & Despesas — snapshots locais + receita pista rápida. */
  async getExpensesDreReport(
    start?: string,
    end?: string,
    company?: number | null
  ): Promise<ExecutiveReport & { fonte?: string; fromCache?: boolean; latencyMs?: number }> {
    const params = new URLSearchParams();
    if (start) params.append("dataInicial", start);
    if (end) params.append("dataFinal", end);
    if (company != null && company > 0) params.append("empresaCodigo", company.toString());
    const query = params.toString() ? `?${params}` : "";
    const envelope = (await fetchDirectApi(
      `/api/v1/executive/reports/expenses${query}`
    )) as {
      success?: boolean;
      data?: ExecutiveReport;
      fonte?: string;
      fromCache?: boolean;
      latencyMs?: number;
    } & ExecutiveReport;
    const payload = (envelope.data || envelope) as ExecutiveReport & {
      fonte?: string;
      fromCache?: boolean;
      latencyMs?: number;
    };
    return {
      ...payload,
      fonte: envelope.fonte ?? payload.fonte,
      fromCache: envelope.fromCache ?? payload.fromCache,
      latencyMs: envelope.latencyMs ?? payload.latencyMs,
    };
  },

  /** Pista & Volumetria — D0 RAM / D-1 DB local (rápido). */
  async getFuelVolumetryReport(
    start?: string,
    end?: string,
    company?: number | null
  ): Promise<ExecutiveReport & { fonte?: string; fromCache?: boolean; latencyMs?: number }> {
    const params = new URLSearchParams();
    if (start) params.append("dataInicial", start);
    if (end) params.append("dataFinal", end);
    if (company != null && company > 0) params.append("empresaCodigo", company.toString());
    const query = params.toString() ? `?${params}` : "";
    const cacheKey = `fuel-vol:${start || ""}:${end || ""}:${company ?? "all"}`;
    try {
      const envelope = (await fetchDirectApi(
        `/api/v1/executive/reports/fuel${query}`,
        { timeoutMs: 2000 } as RequestInit
      )) as {
        success?: boolean;
        data?: ExecutiveReport;
        fonte?: string;
        fromCache?: boolean;
        latencyMs?: number;
      } & ExecutiveReport;
      const payload = (envelope.data || envelope) as ExecutiveReport & {
        fonte?: string;
        fromCache?: boolean;
        latencyMs?: number;
      };
      const result = {
        ...payload,
        fonte: envelope.fonte ?? payload.fonte,
        fromCache: envelope.fromCache ?? payload.fromCache,
        latencyMs: envelope.latencyMs ?? payload.latencyMs,
      };
      try {
        sessionStorage.setItem(cacheKey, JSON.stringify({ ts: Date.now(), result }));
      } catch {
        /* ignore */
      }
      return result;
    } catch (err) {
      try {
        const raw = sessionStorage.getItem(cacheKey);
        if (raw) {
          const parsed = JSON.parse(raw) as { result?: ExecutiveReport & { fonte?: string; fromCache?: boolean; latencyMs?: number } };
          if (parsed?.result) {
            return { ...parsed.result, fromCache: true, fonte: `${parsed.result.fonte || ""}+session_fallback` };
          }
        }
      } catch {
        /* ignore */
      }
      throw err;
    }
  },

  async getPostosInteligencia(
    start: string,
    end: string,
    company?: number | null
  ): Promise<PostosInteligenciaResponse> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company != null && company > 0) params.append("empresaCodigo", String(company));
    const envelope = (await fetchDirectApi(
      `/api/v1/executive/postos-inteligencia?${params}`
    )) as PostosInteligenciaResponse;
    if (!envelope?.unidades) {
      throw new Error("Inteligência dos Postos sem payload");
    }
    return envelope;
  },

  async getExecutiveConsolidatedReportMarkdown(
    start?: string,
    end?: string,
    company?: number
  ): Promise<string> {
    const params = new URLSearchParams();
    if (start) params.append("dataInicial", start);
    if (end) params.append("dataFinal", end);
    if (company) params.append("empresaCodigo", company.toString());
    const query = params.toString() ? `?${params}` : "";
    const data = (await fetchDirectApi(
      `/api/v1/executive/consolidated-report/markdown${query}`
    )) as { markdown: string };
    return data.markdown;
  },

  async getOperationalTanks(
    start: string,
    end: string,
    company?: number
  ): Promise<OperationalTanksResponse> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      const raw = (await fetchDirectApi(
        `/api/v1/operational/fuel-loss?${params}`
      )) as OperationalTanksResponse & { tanks?: TankData[] };
      const tanks = (raw.tanks || []).map((t) => {
        const fuel = String(t.fuel || "");
        const name = String(t.name || "Tanque");
        const isGnv =
          /GNV|GAS NATURAL|\b099\b/i.test(fuel) ||
          /GNV|GAS NATURAL|\b099\b/i.test(name);
        return {
          ...t,
          id: Number(t.id || 0),
          name,
          fuel,
          capacity: Number(t.capacity || 0),
          current: Number(t.current || 0),
          temp: Number(t.temp || 0),
          physical_var: Number(t.physical_var || 0),
          thermal_var: Number(t.thermal_var || 0),
          autonomia_dias:
            t.autonomia_dias === null || t.autonomia_dias === undefined
              ? null
              : Number(t.autonomia_dias),
          // GNV canalizado: nunca "Pedir Carreta"
          alerta_autonomia: isGnv ? "OK" : t.alerta_autonomia || "OK",
          alerta_label: isGnv
            ? "GNV canalizado — sem carreta"
            : t.alerta_label || "Saudável",
        };
      });
      return { tanks, summary: raw.summary || null };
    } catch {
      return { tanks: [], summary: null };
    }
  },

  async getFuelSupply(
    start: string,
    end: string,
    company?: number
  ): Promise<FuelSupplyResponse> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchDirectApi(
        `/api/v1/operational/abastecimentos?${params}`
      )) as FuelSupplyResponse;
    } catch {
      return { abastecimentos: [], summary: null };
    }
  },

  async getExecutiveBriefing(
    dataReferencia?: string,
    company?: number
  ): Promise<{
    dataReferencia: string;
    empresaCodigo?: number | null;
    destaques: Array<{ tipo: string; titulo: string; texto: string }>;
  }> {
    const params = new URLSearchParams();
    if (dataReferencia) params.append("dataReferencia", dataReferencia);
    if (company) params.append("empresaCodigo", company.toString());
    const qs = params.toString();
    return fetchApi(`/api/v1/executive/briefing${qs ? `?${qs}` : ""}`) as Promise<{
      dataReferencia: string;
      empresaCodigo?: number | null;
      destaques: Array<{ tipo: string; titulo: string; texto: string }>;
    }>;
  },

  async getInventoryPrediction(
    empresaCodigo: number,
    diasCobertura: number = 3,
    leadTimeHoras: number = 24
  ): Promise<InventoryPredictionResponse> {
    const params = new URLSearchParams({
      empresaCodigo: empresaCodigo.toString(),
      dias_cobertura: diasCobertura.toString(),
      lead_time_horas: leadTimeHoras.toString(),
    });
    try {
      return (await fetchDirectApi(
        `/api/v1/operational/inventory-prediction?${params}`
      )) as InventoryPredictionResponse;
    } catch {
      return {
        success: false,
        empresa_codigo: empresaCodigo,
        empresa_nome: "",
        data_calculo: "",
        dias_cobertura: diasCobertura,
        lead_time_horas: leadTimeHoras,
        predicoes: [],
        total_sugestao_compra_litros: 0,
        tanques_com_alerta: 0,
        tanques_urgentes: 0,
        observacoes: ["Erro ao buscar previsao"],
      };
    }
  },

  /** Histórico real de descarga (COMPRA / LMC) — Sprint 02 */
  async getTankDischargeHistory(opts: {
    empresaCodigo: number;
    fuel?: string;
    produtoCodigo?: number;
    tanqueId?: number | string;
    dias?: number;
    limit?: number;
  }): Promise<TankDischargeHistoryResponse> {
    const params = new URLSearchParams({
      empresaCodigo: String(opts.empresaCodigo),
      dias: String(opts.dias ?? 45),
      limit: String(opts.limit ?? 20),
    });
    if (opts.fuel) params.append("fuel", opts.fuel);
    if (opts.produtoCodigo != null)
      params.append("produtoCodigo", String(opts.produtoCodigo));
    if (opts.tanqueId != null) params.append("tanqueId", String(opts.tanqueId));
    try {
      return (await fetchDirectApi(
        `/api/v1/operational/tank-discharge-history?${params}`
      )) as TankDischargeHistoryResponse;
    } catch {
      return {
        success: false,
        empresa_codigo: opts.empresaCodigo,
        fonte: "error",
        items: [],
        observacoes: ["Falha ao consultar histórico de descarga"],
      };
    }
  },

  /** Rotas operacionais Sprint 01 — cash/operations (sem fallback fictício) */
  async getCashOperationsSummary(
    start: string,
    end: string,
    company?: number
  ): Promise<{ success?: boolean; data?: unknown; error?: string }> {
    const params = new URLSearchParams({
      dataInicial: start,
      dataFinal: end,
    });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchDirectApi(
        `/api/v1/cash/operations/summary?${params}`
      )) as { success?: boolean; data?: unknown; error?: string };
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : "Erro cash/operations",
      };
    }
  },

  async getExpenseReviewQueue(params: {
    empresaCodigo: number;
    dataInicial: string;
    dataFinal: string;
    status?: string;
    fornecedor?: string;
    plano?: string;
    origem?: string;
    valorMin?: number;
    valorMax?: number;
    pendencias?: boolean;
    divergencias?: boolean;
  }): Promise<ExpenseReviewQueue> {
    const qs = new URLSearchParams({
      empresa_codigo: String(params.empresaCodigo),
      data_inicial: params.dataInicial,
      data_final: params.dataFinal,
    });
    if (params.status) qs.set("status", params.status);
    if (params.fornecedor) qs.set("fornecedor", params.fornecedor);
    if (params.plano) qs.set("plano", params.plano);
    if (params.origem) qs.set("origem", params.origem);
    if (params.valorMin != null) qs.set("valor_min", String(params.valorMin));
    if (params.valorMax != null) qs.set("valor_max", String(params.valorMax));
    if (params.pendencias) qs.set("pendencias", "true");
    if (params.divergencias) qs.set("divergencias", "true");
    return fetchDirectApi(`/api/v1/financial/despesas/revisao?${qs}`) as Promise<ExpenseReviewQueue>;
  },

  async applyExpenseReview(body: ExpenseReviewDecisionInput): Promise<ExpenseReviewItem> {
    return fetchDirectApi(`/api/v1/financial/despesas/revisao`, {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<ExpenseReviewItem>;
  },

  async previewExpenseReviewBatch(body: {
    empresaCodigo: number;
    expenseKeys: string[];
    targetStatus?: string;
    evidenceType?: string;
    assignee?: string;
    dataInicial?: string;
    dataFinal?: string;
  }): Promise<ExpenseReviewBatchPreview> {
    return fetchDirectApi(`/api/v1/financial/despesas/revisao/lote/previsualizar`, {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<ExpenseReviewBatchPreview>;
  },

  async collectExpenseReview(body: {
    empresaCodigo: number;
    dataInicial: string;
    dataFinal: string;
    confirmado: boolean;
  }): Promise<ExpenseReviewQueue> {
    return fetchDirectApi(`/api/v1/financial/despesas/revisao/coletar`, {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<ExpenseReviewQueue>;
  },

  async applyExpenseReviewBatch(body: ExpenseReviewBatchInput): Promise<ExpenseReviewBatchResult> {
    return fetchDirectApi(`/api/v1/financial/despesas/revisao/lote`, {
      method: "POST",
      body: JSON.stringify(body),
    }) as Promise<ExpenseReviewBatchResult>;
  },

  async getExpenseReviewHistory(
    empresaCodigo: number,
    expenseKey: string
  ): Promise<ExpenseReviewHistory> {
    const qs = new URLSearchParams({
      empresa_codigo: String(empresaCodigo),
      expense_key: expenseKey,
    });
    return fetchDirectApi(
      `/api/v1/financial/despesas/revisao/historico?${qs}`
    ) as Promise<ExpenseReviewHistory>;
  },
};

export interface ExpenseReviewItem {
  expenseKey: string;
  expenseReviewId?: string | null;
  empresaCodigo: number;
  data: string;
  fornecedor: string;
  descricao: string;
  valor: number;
  planoConta: string;
  origem?: string | null;
  status: string;
  evidenceType?: string | null;
  assignee?: string | null;
  author?: string | null;
  updatedAt?: string | null;
  observation?: string;
  version: number;
  loteId?: string | null;
}

export interface ExpenseReviewQueue {
  empresaCodigo: number;
  dataInicial?: string;
  dataFinal?: string;
  items: ExpenseReviewItem[];
  coverage: {
    itemCount: number;
    pendingCount: number;
    managerialCoverage: number;
    fiscalCoverage: number;
    statusCounts?: Record<string, number>;
    gateEvidence?: Record<string, boolean | number>;
  };
  automaticActionAllowed: boolean;
  webpostoWrites: number;
  limitations: string[];
  notice?: string;
  maxBatch?: number;
  emptyMessage?: string | null;
  dataSource?: string;
  periodCoverage?: {
    requested: { start: string | null; end: string | null };
    actual: { start: string | null; end: string | null };
  };
  offlineMode?: boolean;
  collectAllowed?: boolean;
}

export interface ExpenseReviewDecisionInput {
  empresaCodigo: number;
  expenseKey: string;
  status: string;
  evidenceType?: string;
  observation?: string;
  assignee?: string;
  expectedVersion: number;
  dataInicial?: string;
  dataFinal?: string;
}

export interface ExpenseReviewBatchPreview {
  empresaCodigo: number;
  dataInicial?: string | null;
  dataFinal?: string | null;
  itemCount: number;
  totalValue: number;
  currentStatusCounts: Record<string, number>;
  targetStatus?: string | null;
  notice?: string;
}

export interface ExpenseReviewBatchInput {
  empresaCodigo: number;
  expenseKeys: string[];
  expectedVersions: Record<string, number>;
  status: string;
  evidenceType?: string;
  observation: string;
  assignee?: string;
  dataInicial?: string;
  dataFinal?: string;
}

export interface ExpenseReviewBatchResult {
  loteId: string;
  itemCount: number;
  items: ExpenseReviewItem[];
  webpostoWrites: number;
  automaticActionAllowed: boolean;
}

export interface ExpenseReviewHistory {
  items: Array<{
    previousStatus?: string | null;
    newStatus: string;
    author: string;
    observation?: string;
    loteId?: string | null;
    createdAt: string;
  }>;
}

export interface TankDischargeItem {
  data: string;
  hora: string;
  litros: number;
  nf: string;
  fornecedor: string;
  produto?: string;
  produto_codigo?: number | null;
  tanque_codigo?: number | null;
  fonte?: string;
}

export interface TankDischargeHistoryResponse {
  success: boolean;
  empresa_codigo: number;
  fonte?: string;
  periodo?: { inicio: string; fim: string };
  items: TankDischargeItem[];
  observacoes?: string[];
}

export interface TankData {
  id: number;
  name: string;
  fuel: string;
  capacity: number;
  current: number;
  temp: number;
  physical_var: number;
  thermal_var: number;
  status: "NORMAL" | "DESVIO_SUSPEITO" | "CRITICO" | "SEM_REGISTRO";
  empresa_codigo: number;
  empresa_nome: string;
  autonomia_dias?: number | null;
  consumo_medio_diario?: number;
  alerta_autonomia?: "OK" | "ATENCAO" | "COMPRA_URGENTE" | string;
  alerta_label?: string;
  estoque_fisico?: number;
  estoque_contabil?: number;
  divergencia_litros?: number;
  divergencia_pct?: number;
  alerta_variancia?: boolean;
  alerta_variancia_label?: string;
  /** ISO WebPosto dataHoraMedidor */
  data_hora_medidor?: string | null;
}

export interface OperationalTanksResponse {
  tanks: TankData[];
  summary: {
    total_desvio: number;
    total_termico: number;
    criticos: number;
    suspeitos: number;
  } | null;
}

export interface FuelSupplyRecord {
  id: number;
  data: string;
  hora: string;
  bico: number;
  produto: string;
  litros: number;
  valor: number;
  encerrante_inicial: number;
  encerrante_final: number;
  empresa_codigo: number;
  empresa_nome: string;
}

export interface FuelSupplyResponse {
  abastecimentos: FuelSupplyRecord[];
  summary: {
    total_litros: number;
    total_valor: number;
    total_transacoes: number;
  } | null;
}
