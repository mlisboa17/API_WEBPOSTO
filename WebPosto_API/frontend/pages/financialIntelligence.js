import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildChartBars, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

function riskBadge(level) {
  const key = String(level || "BAIXO").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  return `<span class="fin-intel-risk fin-intel-risk--${key}">${level || "Não informado"}</span>`;
}

function parseMoney(value) {
  if (value == null || value === "") return null;
  const n = Number(String(value).replace(/[^\d,.-]/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function formatMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return "Dados indisponíveis";
  return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function renderTrendsSection(node, trends) {
  if (!node) return;
  const horizon = trends?.horizons?.["7d"] || {};
  const dims = ["receitas", "despesas", "fluxo", "recebimentos", "pagamentos"];
  node.innerHTML = `
    <div class="fin-ops-grid">
      ${dims
        .map((dim) => {
          const row = horizon[dim] || {};
          return `
          <article class="card fin-ops-card">
            <span>${dim === "receitas" ? "Receitas" : dim === "despesas" ? "Despesas" : dim === "fluxo" ? "Fluxo" : dim === "recebimentos" ? "Recebimentos" : "Pagamentos"}</span>
            <strong>${row.classification || "Não informado"}</strong>
            <small>${row.deltaPct != null ? `${row.deltaPct.toFixed(1)}%` : "Sem referência"}</small>
          </article>`;
        })
        .join("")}
    </div>
  `;
}

function renderRisksSection(node, risks) {
  if (!node) return;
  const rows = Array.isArray(risks?.risks) ? risks.risks : [];
  node.innerHTML = `
    <p class="muted">Nível geral: ${riskBadge(risks?.overallLevel)}</p>
    <ul class="fin-ops-alert-list">
      ${rows
        .map((row) => `<li>${riskBadge(row.level)} <strong>${row.title}</strong></li>`)
        .join("")}
    </ul>
  `;
}

function renderOpportunitiesSection(node, opportunities) {
  if (!node) return;
  const rows = Array.isArray(opportunities?.opportunities) ? opportunities.opportunities : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Nenhuma oportunidade identificada no período.</p>`;
    return;
  }
  node.innerHTML = `
    <ul class="fin-ops-alert-list">
      ${rows
        .slice(0, 6)
        .map((row) => `<li><strong>${row.title}</strong> · impacto ${formatMoney(row.impacto_estimado)}</li>`)
        .join("")}
    </ul>
  `;
}

function renderCashFlowSection(node, cashFlow) {
  if (!node) return;
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card"><span>Saúde do fluxo</span><strong>${cashFlow?.cashFlowHealth || "Dados indisponíveis"}</strong></article>
      <article class="card fin-ops-card"><span>Fluxo atual</span><strong>${formatMoney(cashFlow?.currentFluxo)}</strong></article>
      <article class="card fin-ops-card"><span>Deteriorando?</span><strong>${cashFlow?.fluxoDeteriorando ? "Sim" : "Não"}</strong></article>
    </div>
  `;
}

function renderCommitmentsSection(node, commitments) {
  if (!node) return;
  const rec = commitments?.receivables || {};
  const pay = commitments?.payables || {};
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card"><span>Recebíveis</span><strong>${rec.situacao || rec.health || "Dados indisponíveis"}</strong><small>${formatMoney(rec.total)}</small></article>
      <article class="card fin-ops-card"><span>Pagáveis</span><strong>${pay.situacao || pay.health || "Dados indisponíveis"}</strong><small>${formatMoney(pay.total)}</small></article>
    </div>
  `;
}

export function renderFinancialIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Inteligência",
      message: "Não foi possível montar esta visão no período selecionado.",
      chartTitle: "Indicadores financeiros do período",
    });
    return;
  }

  const data = payload?.data || payload || {};
  const score = data.executiveFinancialScore || {};
  const cards = Array.isArray(data.executiveCards) ? data.executiveCards : [];
  const risks = data.risks?.risks || [];
  const riskLevel = data.risks?.overallLevel || "Não informado";

  const receitaCard = cards.find((c) => /receita/i.test(c.label || ""));
  const despesaCard = cards.find((c) => /despesa/i.test(c.label || ""));

  const receitaNum = parseMoney(receitaCard?.value) ?? parseMoney(data.cashFlow?.currentFluxo);
  const despesaNum = parseMoney(despesaCard?.value);
  const margemNum = receitaNum != null && despesaNum != null ? receitaNum - despesaNum : null;

  const receitaDisplay =
    receitaCard?.value || (receitaNum != null ? moneyKpi(receitaNum) : "Dados indisponíveis");
  const despesaDisplay =
    despesaCard?.value || (despesaNum != null ? moneyKpi(despesaNum) : "Dados indisponíveis");

  const kpis = [
    { label: "Receita", value: receitaDisplay, trendPct: null, status: "ok" },
    { label: "Despesa", value: despesaDisplay, trendPct: null, status: "warn" },
    {
      label: "Margem",
      value: margemNum != null ? moneyKpi(margemNum) : "Dados indisponíveis",
      trendPct: null,
      status: margemNum != null && margemNum < 0 ? "crit" : "ok",
    },
    {
      label: "Alertas",
      value: String(risks.length),
      trendPct: null,
      status: String(riskLevel).toUpperCase().includes("ALTO") ? "crit" : "warn",
    },
  ];

  const topRisk = risks[0];
  const opps = data.opportunities?.opportunities || [];

  const brief = buildFourQuestionBrief({
    what:
      receitaNum != null && despesaNum != null
        ? `Receita ${moneyKpi(receitaNum)} e despesas ${moneyKpi(despesaNum)} no período.`
        : `Situação financeira com ${risks.length} ponto(s) de atenção.`,
    why: topRisk ? topRisk.title : "Indicadores dentro do padrão esperado.",
    where: data.cashFlow?.cashFlowHealth
      ? `Fluxo: ${data.cashFlow.cashFlowHealth}`
      : "Consolidado financeiro da rede",
    actionNow: topRisk
      ? `Mitigar risco: ${topRisk.title}`
      : opps[0]
        ? `Capturar oportunidade: ${opps[0].title}`
        : "Revisar recebíveis e pagáveis pendentes.",
  });

  const chartBars = buildChartBars(cards.slice(0, 6), { labelKey: "label", valueKey: "value", max: 6 });
  const alerts = risks.slice(0, 3).map((r) =>
    enrichAlert(
      {
        severity: r.level || "ALTO",
        title: r.title || "Risco financeiro",
        detail: "",
        view: "expenses",
        origin: "Financeiro",
      },
      {
        why: r.title || "Desvio financeiro detectado",
        where: "Rede / caixa",
        actionNow: "Validar lançamentos e fluxo associado",
      }
    )
  );

  node.innerHTML = buildExecutivePageHtml({
    title: "Inteligência",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Indicadores financeiros do período",
    criticalBranches: [],
    priorityActions: mapPriorityActions(
      alerts.map((a) => ({ title: a.title, detail: a.actionNow, view: a.view }))
    ),
    risks: mapRisks(risks),
    opportunities: mapOpportunities(
      opps.map((o) => ({
        title: o.title,
        impact: o.impacto_estimado != null ? formatMoney(o.impacto_estimado) : "Não informado",
        view: "",
      }))
    ),
    alerts,
    detailHtml: `
      <section class="fin-intel-section card"><h3>Tendências</h3><div id="finIntelTrends"></div></section>
      <section class="fin-intel-section card"><h3>Riscos detalhados</h3><div id="finIntelRisks"></div></section>
      <section class="fin-intel-section card"><h3>Oportunidades</h3><div id="finIntelOpportunities"></div></section>
      <section class="fin-intel-section card"><h3>Fluxo financeiro</h3><div id="finIntelCashFlow"></div></section>
      <section class="fin-intel-section card"><h3>Recebíveis e pagáveis</h3><div id="finIntelCommitments"></div></section>
    `,
    detailSummary: "Análise aprofundada",
  });

  renderTrendsSection(node.querySelector("#finIntelTrends"), data.trends);
  renderRisksSection(node.querySelector("#finIntelRisks"), data.risks);
  renderOpportunitiesSection(node.querySelector("#finIntelOpportunities"), data.opportunities);
  renderCashFlowSection(node.querySelector("#finIntelCashFlow"), data.cashFlow);
  renderCommitmentsSection(node.querySelector("#finIntelCommitments"), data.commitments);
}
