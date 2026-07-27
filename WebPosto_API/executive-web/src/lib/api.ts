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

  async getExecutiveConsolidatedReport(): Promise<ExecutiveReport> {
    return fetchDirectApi("/api/v1/executive/consolidated-report") as Promise<ExecutiveReport>;
  },

  async getExecutiveConsolidatedReportMarkdown(): Promise<string> {
    const data = (await fetchDirectApi(
      "/api/v1/executive/consolidated-report/markdown"
    )) as { markdown: string };
    return data.markdown;
  },
};
