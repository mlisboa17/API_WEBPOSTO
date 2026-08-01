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
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";
const API_PREFIX = "/api/proxy";

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const proxyEndpoint = endpoint.startsWith("/api/v1/") 
    ? `${API_PREFIX}${endpoint.replace("/api/v1/", "/")}`
    : endpoint;

  const url = `${API_BASE_URL}${proxyEndpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

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
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

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

  async getCardFraudAudit(
    start: string,
    end: string,
    company?: number,
    limiarRetencaoMinutos?: number | null
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
    try {
      const raw = (await fetchApi(
        `/api/v1/executive/audit/card-fraud?${params}`
      )) as CardFraudAuditResponse & { data?: CardFraudAuditResponse };
      if (raw && typeof raw === "object" && raw.data && (raw.data.resumo || raw.data.resumoExecutivo)) {
        const d = raw.data;
        return {
          ...d,
          success: d.success !== false,
          resumo: d.resumo || d.resumoExecutivo || d.resumo,
          resumoExecutivo: d.resumoExecutivo || d.resumo,
        } as CardFraudAuditResponse;
      }
      return raw as CardFraudAuditResponse;
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
