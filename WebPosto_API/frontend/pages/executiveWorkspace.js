import { buildExecutiveWorkspace } from "../services/workspaceEngine.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { bindExecutiveNav } from "../components/executiveFirstFold.js";
import { buildChartBars, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

function renderOpportunities(items = []) {
  if (!items.length) return `<p class="muted">Nenhuma oportunidade priorizada no momento.</p>`;
  return `
    <table class="data-table ws-table">
      <thead><tr><th>Oportunidade</th><th>Impacto</th><th>Filial</th><th>Prioridade</th><th>Responsável</th></tr></thead>
      <tbody>
        ${items
          .slice(0, 8)
          .map(
            (item) => `
              <tr data-nav-view="${item.view}">
                <td>${item.title}</td>
                <td>${item.impact}</td>
                <td>${item.filial}</td>
                <td>${item.priority}</td>
                <td>${item.owner}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderBranchList(title, rows = []) {
  if (!rows.length) return `<p class="muted">Sem dados para ${title}.</p>`;
  return `
    <ul class="ws-branch-list">
      ${rows
        .map(
          (row) => `
            <li>
              <span>${row.filial}</span>
              <strong>${row.metric}</strong>
              <em>${row.tag}</em>
            </li>
          `
        )
        .join("")}
    </ul>
  `;
}

export function renderExecutiveWorkspace(node, data, filters, options = {}) {
  if (!node) return;
  if (!data) {
    node.innerHTML = `<p class="muted">Dados indisponíveis para este período.</p>`;
    return;
  }

  const workspace = buildExecutiveWorkspace(data);
  const summary = workspace.summary || [];
  const receitaRaw = summary.find((s) => s.key === "receita")?.value;
  const margemRaw = summary.find((s) => s.key === "margem")?.value;
  const receita =
    receitaRaw == null || receitaRaw === "" || receitaRaw === "—" ? "Dados indisponíveis" : receitaRaw;
  const margem =
    margemRaw == null || margemRaw === "" || margemRaw === "—" ? "Dados indisponíveis" : margemRaw;
  const despesaVal = moneyKpi(workspace.execution?.despesaTotal);
  const alertCount = (workspace.alerts || []).length;

  const kpis = [
    { label: "Receita", value: receita, trendPct: null, status: "ok" },
    {
      label: "Despesa",
      value: despesaVal,
      trendPct: null,
      status: "warn",
    },
    { label: "Margem", value: margem, trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: String(alertCount),
      trendPct: null,
      status: alertCount > 0 ? "crit" : "ok",
    },
  ];

  const chartBars = buildChartBars(
    summary.map((s) => ({ label: s.label, value: parseFloat(String(s.value).replace(/[^\d,.-]/g, "").replace(",", ".")) || s.hint })),
    { labelKey: "label", valueKey: "value", max: 4 }
  );

  const topAlert = (workspace.alerts || [])[0];
  const topRiskBranch = (workspace.branches?.risk || [])[0];
  const brief = buildFourQuestionBrief({
    what: `A rede registrou receita ${receita} e margem ${margem} no período.`,
    why: topAlert
      ? `${topAlert.origin}: ${topAlert.title} — ${topAlert.detail || "desvio operacional"}.`
      : "Indicadores dentro do padrão esperado para o recorte.",
    where: topRiskBranch?.filial || topAlert?.detail?.split("·")[0]?.trim() || "Consolidado da rede",
    actionNow: topAlert
      ? `Tratar hoje: ${topAlert.title} (${topAlert.origin}).`
      : "Executar oportunidades comerciais de maior impacto.",
  });

  const enrichedAlerts = (workspace.alerts || []).slice(0, 3).map((alert) =>
    enrichAlert(alert, {
      why: alert.detail,
      where: alert.origin,
      actionNow: `Abrir ${alert.origin} e resolver ${alert.title.toLowerCase()}`,
    })
  );

  const detail = `
    <section class="ws-block ws-block--opps">
      <h3>Oportunidades</h3>
      ${renderOpportunities(workspace.opportunities)}
    </section>
    <section class="ws-block">
      <h3>Desempenho por filial</h3>
      <div class="ws-branch-grid">
        <article><h4>Top filiais</h4>${renderBranchList("top", workspace.branches.top)}</article>
        <article><h4>Filiais em risco</h4>${renderBranchList("risco", workspace.branches.risk)}</article>
        <article><h4>Sem LMC</h4>${renderBranchList("LMC", workspace.branches.semLmc)}</article>
      </div>
    </section>
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: "Resumo",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Indicadores consolidados da rede",
    criticalBranches: mapCriticalBranches(
      (workspace.branches?.risk || []).map((row) => ({
        name: row.filial,
        metric: row.metric,
        tag: row.tag,
        view: "fuelGovernance",
      }))
    ),
    priorityActions: mapPriorityActions(
      (workspace.alerts || [])
        .filter((a) => a.view)
        .map((a) => ({ title: a.title, detail: a.origin, view: a.view }))
    ),
    risks: mapRisks(
      (workspace.alerts || []).map((a) => ({ title: a.title, detail: a.detail, severity: a.severity }))
    ),
    opportunities: mapOpportunities(workspace.opportunities || []),
    alerts: enrichedAlerts,
    detailHtml: detail,
    detailSummary: "Detalhamento operacional",
  });

  bindExecutiveNav(node, options.onNavigate);
  node.querySelectorAll("[data-nav-view]").forEach((el) => {
    if (el.classList.contains("exec-alert__action")) return;
    el.addEventListener("click", () => {
      const view = el.getAttribute("data-nav-view");
      if (view) options.onNavigate?.(view);
    });
  });
}
