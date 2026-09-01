/** Normalização dos payloads executivos (DRE, cash-flow, combustível, business-health). */

export const EXECUTIVE_UNAVAILABLE_MSG = "Dados indisponíveis para esta filial";

function toNumber(value) {
  const normalized = Number(String(value ?? 0).replace(",", "."));
  return Number.isFinite(normalized) ? normalized : 0;
}

export function unavailablePayload(message = EXECUTIVE_UNAVAILABLE_MSG) {
  return { unavailable: true, message };
}

export function normalizeDre(raw) {
  if (!raw) return null;
  if (raw.unavailable) return raw;

  const faturamentoBruto = raw.faturamentoBruto ?? raw.receitas ?? "0";
  const deducoes = raw.deducoes ?? "0";
  const custosProduto = raw.custosProduto ?? raw.custos ?? "0";
  const margemContribuicao =
    raw.margemContribuicao ??
    String(toNumber(faturamentoBruto) - toNumber(deducoes) - toNumber(custosProduto));
  const despesasOperacionais =
    raw.despesasOperacionais ?? raw.outrasDespesas ?? raw.despesas ?? "0";
  const resultadoOperacional = raw.resultadoOperacional ?? raw.resultado ?? "0";

  return {
    ...raw,
    receitas: raw.receitas ?? faturamentoBruto,
    faturamentoBruto,
    deducoes,
    custosProduto,
    margemContribuicao,
    despesasOperacionais,
    outrasDespesas: raw.outrasDespesas ?? despesasOperacionais,
    resultadoOperacional,
    margemPct: raw.margemPct ?? raw.margemPercentual ?? "0",
    porFilial: Array.isArray(raw.porFilial) ? raw.porFilial : [],
    estruturaGerencial: raw.estruturaGerencial ?? {
      faturamentoBruto,
      deducoes,
      margemContribuicao,
      despesasOperacionais,
      resultadoOperacional,
    },
  };
}

export function normalizeCashFlow(raw) {
  if (!raw) return null;
  if (raw.unavailable) return raw;

  const breakdown = raw.semanticBreakdown || {};
  return {
    ...raw,
    cards: raw.cards || {},
    daily: raw.daily || [],
    weekly: raw.weekly || [],
    monthly: raw.monthly || [],
    semanticBreakdown: {
      despesas: breakdown.despesas || [],
      receitas: breakdown.receitas || [],
      despesasPrevistas: breakdown.despesasPrevistas || [],
      receitasPrevistas: breakdown.receitasPrevistas || [],
    },
  };
}

export function normalizeFuelExecutive(raw) {
  if (!raw) return null;
  if (raw.unavailable) return raw;

  const paridadePrecos = Array.isArray(raw.paridadePrecos) ? raw.paridadePrecos : [];
  const precificacao = raw.precificacao || {};
  const kpis = { ...(raw.kpis || {}) };

  if (precificacao.litrosTotal != null) kpis.litrosVendidos = kpis.litrosVendidos ?? precificacao.litrosTotal;
  if (precificacao.margemMediaRealizadaPct != null) {
    kpis.margemMediaRealizadaPct = precificacao.margemMediaRealizadaPct;
  }
  if (precificacao.margemMetaPct != null) kpis.margemMetaPct = precificacao.margemMetaPct;

  return {
    ...raw,
    paridadePrecos,
    precificacao: {
      litrosTotal: precificacao.litrosTotal ?? raw.litrosTotal ?? kpis.litrosVendidos ?? "0",
      combustiveisAnalisados: precificacao.combustiveisAnalisados ?? paridadePrecos.length,
      margemMediaRealizadaPct: precificacao.margemMediaRealizadaPct,
      margemMetaPct: precificacao.margemMetaPct,
    },
    kpis,
  };
}

export function normalizeBusinessHealth(raw) {
  if (!raw) return null;
  if (raw.unavailable) return raw;

  return {
    overall_score: raw.overall_score ?? 0,
    status: raw.status ?? "unknown",
    risk_count: raw.risk_count ?? 0,
    has_sufficient_data: raw.has_sufficient_data !== false,
    message: raw.message ?? null,
    last_update: raw.last_update ?? null,
    deductions: Array.isArray(raw.deductions) ? raw.deductions : [],
    formula: raw.formula ?? null,
    snapshot: raw.snapshot,
  };
}
