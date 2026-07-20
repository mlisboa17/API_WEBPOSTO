import { formatCurrency } from "./format.js";
import { LICENSED_COMPANIES, MANAGEMENT_DEPARTMENTS, WEBPOSTO_GROUP_DEPARTMENT_MAP } from "../config/managementScope.js";

const MONEY_KEYS = [
  "receita",
  "faturamento",
  "totalVendas",
  "total_vendas",
  "valorTotal",
  "valor_total",
  "totalVenda",
  "bruto",
];

const EXPENSE_KEYS = ["valor", "valorTotal", "valor_total", "total", "despesa"];
const LITER_KEYS = ["litros", "volume", "quantidade", "qtd"];
const MARGIN_KEYS = ["margem", "margemBruta", "lucroBruto", "lucro_bruto"];

function rows(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.resultados)) return payload.resultados;
  if (Array.isArray(payload?.operations)) return payload.operations;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.postos)) return payload.postos;
  return [];
}

function num(value) {
  if (value == null || value === "") return null;
  const text = String(value).trim();
  const normalized = text.includes(",")
    ? text.replace(/\./g, "").replace(",", ".")
    : text;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function firstNumber(source, keys) {
  if (!source || typeof source !== "object") return null;
  for (const key of keys) {
    const value = num(source[key]);
    if (value != null) return value;
  }
  return null;
}

function firstPositiveNumber(source, keys) {
  const value = firstNumber(source, keys);
  return value != null && value > 0 ? value : null;
}

function sumByKeys(items, keys) {
  let total = 0;
  let hasValue = false;
  for (const item of items) {
    const value = firstNumber(item, keys);
    if (value != null) {
      total += value;
      hasValue = true;
    }
  }
  return hasValue ? total : null;
}

function pickLabel(item, keys, fallback = "Nao informado") {
  for (const key of keys) {
    const value = item?.[key];
    if (value != null && String(value).trim()) return String(value).trim();
  }
  return fallback;
}

function pct(current, previous) {
  if (current == null || previous == null || previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

function fmtMoney(value) {
  return value == null ? "Dados indisponiveis" : formatCurrency(value);
}

function fmtPct(value) {
  if (value == null || !Number.isFinite(value)) return "Sem comparativo";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function normalizedText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
}

function departmentId(row) {
  const groupCode = String(row?.grupoCodigo ?? row?.grupoProdutoCodigo ?? row?.codigoGrupo ?? "");
  if (WEBPOSTO_GROUP_DEPARTMENT_MAP[groupCode]) return WEBPOSTO_GROUP_DEPARTMENT_MAP[groupCode];
  const text = normalizedText([
    row?.departamento,
    row?.departamentoNome,
    row?.setor,
    row?.grupo,
    row?.categoria,
    row?.produto,
    row?.descricao,
  ].filter(Boolean).join(" "));
  if (/COMBUST|GASOLINA|ETANOL|DIESEL|GNV/.test(text)) return "combustiveis";
  if (/LUBRIFIC|OLEO MOTOR|ADITIVO|FLUIDO|FILTRO|PALHETA|GRAXA/.test(text)) return "lubrificantes";
  if (/CONVENI|LOJA|BEBIDA|ALIMENTO|CIGARRO|TABACO|BAZAR|FAST FOOD|MERCEARIA|SALGADINHO|BISCOITO|SORVETE|GELO|BOMBON|AGUA RETORN/.test(text)) return "conveniencia";
  return null;
}

function buildDepartments(raw) {
  const salesRows = rows(raw.sales);
  return MANAGEMENT_DEPARTMENTS.map((department) => {
    const departmentSales = salesRows.filter((row) => departmentId(row) === department.id);
    const revenue = sumByKeys(departmentSales, MONEY_KEYS);
    const fuelRevenue = department.id === "combustiveis" ? sumByKeys(rows(raw.fuelSummary), MONEY_KEYS) : null;
    const resolvedRevenue = revenue ?? fuelRevenue;
    return {
      ...department,
      revenue: resolvedRevenue,
      revenueLabel: resolvedRevenue == null ? "Não identificado na origem" : fmtMoney(resolvedRevenue),
      status: resolvedRevenue == null ? "pending" : "available",
      detail: resolvedRevenue == null
        ? "O WebPosto não retornou classificação departamental suficiente para este recorte."
        : `${departmentSales.length || rows(raw.fuelSummary).length} registro(s) classificados sem mistura com outros departamentos.`,
    };
  });
}

function normalizeFuelName(item) {
  return pickLabel(item, ["combustivel", "produto", "nomeProduto", "categoria", "descricao"], "Combustivel");
}

function buildFuelMix(fuelSummary) {
  const items = rows(fuelSummary);
  const mapped = items
    .map((item) => ({
      label: normalizeFuelName(item),
      value: firstNumber(item, LITER_KEYS),
      revenue: firstNumber(item, MONEY_KEYS),
      margin: firstNumber(item, MARGIN_KEYS),
    }))
    .filter((item) => item.value != null || item.revenue != null);

  const totalLiters = sumByKeys(mapped, ["value"]);
  return mapped
    .map((item) => ({
      ...item,
      share: totalLiters && item.value != null ? (item.value / totalLiters) * 100 : null,
    }))
    .sort((a, b) => Number(b.value || b.revenue || 0) - Number(a.value || a.revenue || 0))
    .slice(0, 6);
}

function buildBranchRanking(scorecard, sales) {
  const sourceOptions = [
    rows(scorecard?.cockpit?.topFiliais || scorecard?.data?.cockpit?.topFiliais),
    rows(scorecard?.peopleScorecard?.topFiliais),
    scorecard?.financialScorecard?.roiBenchmark ? [scorecard.financialScorecard.roiBenchmark] : [],
    rows(sales),
  ];
  const sourceRows = sourceOptions.find((items) => items.length) || [];
  const companyByCode = new Map(LICENSED_COMPANIES.map((company) => [company.empresaCodigo, company]));
  const totals = new Map(LICENSED_COMPANIES.map((company) => [company.empresaCodigo, null]));

  for (const item of sourceRows) {
    const rawCode = String(item?.empresaCodigo ?? item?.codigoEmpresa ?? item?.filialCodigo ?? "");
    let company = companyByCode.get(rawCode);
    if (!company) {
      const rawName = normalizedText(pickLabel(item, ["nomeFilial", "filial", "empresaNome", "nomeFantasia"], ""));
      company = LICENSED_COMPANIES.find((candidate) => {
        const officialName = normalizedText(candidate.nome);
        return rawName === officialName || rawName.includes(officialName) || officialName.includes(rawName);
      });
    }
    if (!company) continue;
    const value = firstNumber(item, ["receita", ...MONEY_KEYS]);
    if (value == null) continue;
    totals.set(company.empresaCodigo, (totals.get(company.empresaCodigo) || 0) + value);
  }

  return LICENSED_COMPANIES
    .map((company) => ({
      empresaCodigo: company.empresaCodigo,
      label: company.nome,
      value: totals.get(company.empresaCodigo),
      available: totals.get(company.empresaCodigo) != null,
    }))
    .sort((a, b) => Number(b.value ?? -1) - Number(a.value ?? -1));
}

function scorecardRevenue(scorecard) {
  return (
    firstPositiveNumber(scorecard?.financialScorecard, ["receitaOperacional", "receitaRede", "receita"]) ??
    firstPositiveNumber(scorecard?.financialScorecard?.roiBenchmark, ["receita"]) ??
    firstPositiveNumber(scorecard?.executiveKpiEngine?.evidence, ["receitaOperacional"])
  );
}

function scorecardMargin(scorecard) {
  const roi = scorecard?.financialScorecard?.roiBenchmark;
  return firstNumber(scorecard?.financialScorecard, ["resultadoOperacional", "lucro", "lucroBruto"]) ?? firstNumber(roi, ["lucro"]);
}

function scorecardTicket(scorecard) {
  return firstPositiveNumber(scorecard?.commercialScorecard, ["ticketMedio", "ticket_medio"]);
}

function buildStockTurnover(stock, fuelSummary) {
  const stockValue = sumByKeys(rows(stock), ["estoqueAtual", "saldo", "quantidade", "qtdEstoque"]);
  const soldLiters = sumByKeys(rows(fuelSummary), LITER_KEYS);
  if (stockValue == null || soldLiters == null || stockValue === 0) return null;
  return soldLiters / stockValue;
}

function collectAlerts({ revenueTrend, expenseRatio, fuelMix, stockTurnover, branchRanking }) {
  const alerts = [];
  if (revenueTrend != null && revenueTrend < -5) {
    alerts.push({ tone: "bad", title: "Queda de receita", detail: `Receita caiu ${Math.abs(revenueTrend).toFixed(1)}% contra o periodo anterior.` });
  }
  if (expenseRatio != null && expenseRatio > 8) {
    alerts.push({ tone: "bad", title: "Custo acima do alvo", detail: `Despesas representam ${expenseRatio.toFixed(1)}% da receita.` });
  }
  const weakMargin = fuelMix.find((item) => item.margin != null && item.margin < 0);
  if (weakMargin) {
    alerts.push({ tone: "bad", title: "Margem negativa", detail: `${weakMargin.label} aparece com margem abaixo de zero.` });
  }
  if (stockTurnover != null && stockTurnover < 0.05) {
    alerts.push({ tone: "warn", title: "Giro baixo", detail: "Estoque girando pouco para o volume vendido no periodo." });
  }
  if (!branchRanking.length) {
    alerts.push({ tone: "warn", title: "Ranking incompleto", detail: "Dados reais por filial nao retornaram para este recorte." });
  }
  return alerts.slice(0, 5);
}

function collectInsights({ revenueTrend, fuelMix, expenseRatio, branchRanking }) {
  const insights = [];
  if (revenueTrend != null) {
    insights.push({
      tone: revenueTrend >= 0 ? "good" : "bad",
      text: `Receita ${revenueTrend >= 0 ? "cresceu" : "caiu"} ${Math.abs(revenueTrend).toFixed(1)}% contra o periodo anterior.`,
    });
  }
  if (fuelMix[0]?.share != null) {
    insights.push({ tone: "good", text: `${fuelMix[0].label} lidera o mix com ${fuelMix[0].share.toFixed(1)}% do volume.` });
  }
  if (expenseRatio != null) {
    insights.push({
      tone: expenseRatio <= 5 ? "good" : "warn",
      text: `Despesas equivalem a ${expenseRatio.toFixed(1)}% da receita consolidada.`,
    });
  }
  if (branchRanking[0]) {
    insights.push({ tone: "good", text: `${branchRanking[0].label} lidera o ranking de receita no periodo.` });
  }
  return insights;
}

export function buildPresidentDashboardData(raw) {
  const scorecard = raw.scorecard?.data ?? raw.scorecard;
  const currentRevenue =
    scorecardRevenue(scorecard) ??
    firstPositiveNumber(raw.kpis, MONEY_KEYS) ??
    firstPositiveNumber(raw.overview, MONEY_KEYS) ??
    firstPositiveNumber(raw.sales?.consolidado, MONEY_KEYS) ??
    sumByKeys(rows(raw.sales), MONEY_KEYS);
  const previousRevenue =
    firstPositiveNumber(raw.previousKpis, MONEY_KEYS) ??
    firstPositiveNumber(raw.previousOverview, MONEY_KEYS);
  const expenses = sumByKeys(rows(raw.expenses), EXPENSE_KEYS);
  const fuelMix = buildFuelMix(raw.fuelSummary);
  const branchRanking = buildBranchRanking(scorecard, raw.sales);
  const stockTurnover = buildStockTurnover(raw.stock, raw.fuelSummary);
  const revenueTrend = pct(currentRevenue, previousRevenue);
  const expenseRatio = currentRevenue && expenses != null ? (expenses / currentRevenue) * 100 : null;
  const marginValue = currentRevenue == null ? null : scorecardMargin(scorecard) ?? firstNumber(raw.kpis, MARGIN_KEYS) ?? firstNumber(raw.overview, MARGIN_KEYS);
  const marginPct = currentRevenue && marginValue != null ? (marginValue / currentRevenue) * 100 : null;
  const ticket = scorecardTicket(scorecard) ?? firstPositiveNumber(raw.kpis, ["ticketMedio", "ticket_medio"]) ?? firstPositiveNumber(raw.sales?.consolidado, ["ticketMedio", "ticket_medio"]);

  const context = { revenueTrend, expenseRatio, fuelMix, stockTurnover, branchRanking };
  const reconciliation = raw.directorReconciliation || {};
  const publication = reconciliation.publication || {};
  const dreLines = raw.completeDre?.lines || [];
  const companyMap = new Map(LICENSED_COMPANIES.map((item) => [Number(item.empresaCodigo), item.nome]));
  const departmentMatrix = dreLines.length
    ? dreLines.map((line) => ({ ...line, companyName: line.companyName || companyMap.get(Number(line.companyCode)) }))
    : LICENSED_COMPANIES.flatMap((company) => MANAGEMENT_DEPARTMENTS.map((department) => ({
        companyCode: company.empresaCodigo,
        companyName: company.nome,
        department: department.id,
        status: "BLOQUEADO",
        revenue: null,
        cost: null,
        grossMargin: null,
        expenses: null,
        operatingResult: null,
        operatingMarginPct: null,
      })));
  return {
    kpis: [
      { label: "Receita consolidada", value: fmtMoney(currentRevenue), raw: currentRevenue, tone: revenueTrend == null || revenueTrend >= 0 ? "good" : "bad", delta: fmtPct(revenueTrend) },
      { label: "Lucro / margem", value: marginValue == null ? "Dados indisponiveis" : fmtMoney(marginValue), raw: marginValue, tone: marginPct == null || marginPct >= 10 ? "good" : "warn", delta: marginPct == null ? "Sem margem" : `${marginPct.toFixed(1)}%` },
      { label: "Despesas vs receita", value: expenses == null ? "Dados indisponiveis" : fmtMoney(expenses), raw: expenses, tone: expenseRatio == null || expenseRatio <= 5 ? "good" : "bad", delta: expenseRatio == null ? "Sem proporcao" : `${expenseRatio.toFixed(1)}%` },
      { label: "Ticket medio", value: ticket == null ? "Dados indisponiveis" : fmtMoney(ticket), raw: ticket, tone: "neutral", delta: "Periodo atual" },
    ],
    branchRanking,
    fuelMix,
    stockTurnover,
    alerts: collectAlerts(context),
    insights: collectInsights(context),
    departments: buildDepartments(raw),
    departmentMatrix,
    homologation: {
      released: publication.dreTotalsReleased === true,
      sourceCoverageComplete: publication.sourceCoverageComplete === true,
      classificationComplete: publication.departmentalClassificationComplete === true,
      pendingExpenses: Number(reconciliation.departmentGovernance?.unclassified || reconciliation.reviewableFacts?.length || 0),
      conflicts: Number(reconciliation.departmentGovernance?.conflicts || 0),
    },
    source: raw,
  };
}
