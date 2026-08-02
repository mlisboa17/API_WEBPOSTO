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
  CashierAuditResponse,
  PistaLiveResponse,
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
    return await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (err) {
    throw new Error(networkErrorMessage(err));
  }
}

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const proxyEndpoint = endpoint.startsWith("/api/v1/") 
    ? `${API_PREFIX}${endpoint.replace("/api/v1/", "/")}`
    : endpoint;

  const url = `${API_BASE_URL}${proxyEndpoint}`;
  const response = await browserFetch(url, options);

  if (!response.ok) {
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json() as { error?: string; message?: string };
      errorMessage = errorData.error || errorData.message || errorMessage;
    } catch {
      // Not JSON, use default status text
    }
    throw new Error(errorMessage);
  }

  const contentType = response.headers.get("content-type");
  if (!contentType || !contentType.includes("application/json")) {
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

  if (!response.ok) {
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    try {
      const errorData = (await response.json()) as { error?: string; message?: string };
      errorMessage = errorData.error || errorData.message || errorMessage;
    } catch {
      // Not JSON, use default status text
    }
    throw new Error(errorMessage);
  }

  const contentType = response.headers.get("content-type");
  if (!contentType || !contentType.includes("application/json")) {
    throw new Error("Resposta da API não é um JSON válido");
  }

  return response.json();
}

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

  async getCompleteDre(start: string, end: string, company?: number): Promise<{ lines: DreLine[] }> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    return fetchApi(`/api/v1/executive/dashboard?${params}`) as Promise<{ lines: DreLine[] }>;
  },

  async getReviewableFacts(start: string, end: string, company?: number): Promise<ReviewableFact[]> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    const data = await fetchApi(`/api/v1/executive/dashboard?${params}`) as { directorReconciliation?: { reviewableFacts?: ReviewableFact[] } };
    return data.directorReconciliation?.reviewableFacts || [];
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

  async getDataAudit(start: string, end: string, company?: number): Promise<DataAuditResponse> {
    const params = new URLSearchParams({ dataInicial: start, dataFinal: end });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchApi(`/api/v1/executive/data-audit?${params}`)) as DataAuditResponse;
    } catch {
      return {
        periodo: { inicio: start, fim: end },
        filiais: [],
        consolidado: {},
        success: false,
        mensagem: "Fallback local — data-audit indisponível",
      };
    }
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
      categoriaPlanoContas,
    });
    if (company) params.append("empresaCodigo", company.toString());
    try {
      return (await fetchApi(
        `/api/v1/executive/expenses/details?${params}`
      )) as ExpenseDetailsResponse;
    } catch (err) {
      return {
        empresaCodigo: company ?? null,
        periodo: { inicio: start, fim: end },
        categoria: categoriaPlanoContas,
        categoriaKey: categoriaPlanoContas,
        subtotal: 0,
        quantidade: 0,
        itens: [],
        success: false,
        mensagem: err instanceof Error ? err.message : "Falha ao carregar detalhes",
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
    } catch {
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
    const envelope = (await fetchDirectApi(
      `/api/v1/executive/reports/fuel${query}`
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
      const tanks = (raw.tanks || []).map((t) => ({
        ...t,
        id: Number(t.id || 0),
        name: t.name || "Tanque",
        fuel: t.fuel || "",
        capacity: Number(t.capacity || 0),
        current: Number(t.current || 0),
        temp: Number(t.temp || 0),
        physical_var: Number(t.physical_var || 0),
        thermal_var: Number(t.thermal_var || 0),
        autonomia_dias:
          t.autonomia_dias === null || t.autonomia_dias === undefined
            ? null
            : Number(t.autonomia_dias),
        alerta_autonomia: t.alerta_autonomia || "OK",
        alerta_label: t.alerta_label || "Saudável",
      }));
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
    destaques: Array<{ tipo: string; titulo: string; texto: string }>;
  }> {
    const params = new URLSearchParams();
    if (dataReferencia) params.append("dataReferencia", dataReferencia);
    if (company) params.append("empresaCodigo", company.toString());
    const qs = params.toString();
    return fetchApi(`/api/v1/executive/briefing${qs ? `?${qs}` : ""}`) as Promise<{
      dataReferencia: string;
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
};

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
