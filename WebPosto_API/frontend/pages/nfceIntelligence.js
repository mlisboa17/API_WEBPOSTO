import { downloadCsv } from "../services/export.js";
import { bindExecutiveNav, renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

const FISCAL_EMPTY_MSG = "Não foi possível montar esta visão no período selecionado.";

function panelText(value, fallback = "Não informado") {
  if (value == null || value === "" || value === "—") return fallback;
  return value;
}

function cellText(value) {
  if (value == null || value === "" || value === "—") return "Não informado";
  return value;
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .filter(Boolean)
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          return `<td>${cellText(val)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

function renderPatterns(items) {
  if (!items?.length) return "";
  const cards = items
    .map(
      (item) => `
    <article class="panel fiscal-pattern-card">
      <p><strong>${cellText(item.tipo)}</strong></p>
      <p class="muted">Valor: ${cellText(item.valor)} · Prioridade: ${cellText(item.severidade)}</p>
    </article>
  `
    )
    .join("");
  return `<section class="panel"><h3>Principais ocorrências</h3>${cards}</section>`;
}

export function renderNfceIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "NFCE",
      message: FISCAL_EMPTY_MSG,
      chartTitle: "Divergências por filial",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const recon = payload.nfceReconciliationEngine || cockpit.reconciliacao || {};
  const risks = payload.nfceRiskEngine?.risks || cockpit.riscoFiscal || [];
  const patterns = payload.nfceAnomalyEngine?.patterns || cockpit.topOcorrencias || [];
  const execIntel = payload.nfceExecutiveIntelligence || cockpit.executiveIntelligence || {};

  const emitidas = exec["2_emitidas"] ?? cockpit.nfceEmitidas ?? 0;
  const canceladas = exec["3_canceladas"] ?? cockpit.nfceCanceladas ?? 0;
  const cobertura = exec["6_coberturaReconciliacao"] ?? recon.coveragePct ?? null;
  const divergencias = exec["8_divergencias"] ?? cockpit.divergencias ?? 0;
  const hasData = Number(emitidas) > 0 || risks.length > 0 || patterns.length > 0;

  if (!hasData) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "NFCE",
      message: FISCAL_EMPTY_MSG,
      chartTitle: "Divergências por filial",
    });
    return;
  }

  const kpis = [
    { label: "Emitidas", value: countKpi(emitidas), trendPct: null, status: "ok" },
    { label: "Canceladas", value: countKpi(canceladas), trendPct: null, status: Number(canceladas) > 0 ? "warn" : "ok" },
    {
      label: "Cobertura",
      value: cobertura != null ? `${cobertura}%` : "Dados indisponíveis",
      trendPct: null,
      status: Number(cobertura) >= 90 ? "ok" : "warn",
    },
    {
      label: "Alertas",
      value: String(divergencias || risks.length || 0),
      trendPct: null,
      status: Number(divergencias) > 0 ? "crit" : "ok",
    },
  ];

  const topRisk = risks[0];
  const brief = buildFourQuestionBrief({
    what: `${emitidas} notas emitidas; ${divergencias} divergência(s); cobertura ${cobertura != null ? `${cobertura}%` : "indisponível"}.`,
    why: topRisk
      ? `Risco ${panelText(topRisk.risco)} com ${topRisk.cancelamentos ?? 0} cancelamento(s).`
      : Number(canceladas) > 0
        ? `${canceladas} notas canceladas impactam conformidade.`
        : "Operação fiscal estável no recorte.",
    where: execIntel.filialMaiorRisco?.empresaCodigo
      ? `Filial ${execIntel.filialMaiorRisco.empresaCodigo}`
      : topRisk?.empresaCodigo
        ? `Filial ${topRisk.empresaCodigo}`
        : "Rede consolidada",
    actionNow: topRisk
      ? `Reconciliar notas da filial ${topRisk.empresaCodigo || "crítica"} hoje.`
      : "Manter rotina de conciliação diária.",
  });

  const chartBars = buildChartBars(risks, { labelKey: "empresaCodigo", valueKey: "divergencias", max: 7 });
  const alerts = risks.slice(0, 3).map((r) =>
    enrichAlert(
      {
        severity: r.risco || "ALTO",
        title: `Risco fiscal — filial ${panelText(r.empresaCodigo)}`,
        detail: `${r.divergencias ?? 0} divergências · ${r.cancelamentos ?? 0} cancelamentos`,
        view: "fiscalReconciliation",
        origin: "Fiscal",
      },
      {
        why: `${r.cancelamentos ?? 0} cancelamentos · ${r.ausencias ?? 0} ausências`,
        where: r.empresaCodigo ? `Filial ${r.empresaCodigo}` : "Rede",
        actionNow: "Abrir conciliação fiscal",
      }
    )
  );

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="nfceIntelRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="nfceIntelExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${renderPatterns(patterns)}
    ${renderTable("Risco por filial", risks, [
      { key: "empresaCodigo", label: "Filial" },
      { key: "risco", label: "Risco" },
      { key: "cancelamentos", label: "Cancelamentos" },
      { key: "ausencias", label: "Ausências" },
      { key: "divergencias", label: "Divergências" },
    ])}
    ${renderTable("Situação de conciliação", recon.items || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Quantidade" },
    ])}
    ${
      execIntel.filialMaiorRisco
        ? `<p class="muted">Filial de maior risco: ${panelText(execIntel.filialMaiorRisco.empresaCodigo)}</p>`
        : ""
    }
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "NFCE",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Divergências por filial",
    criticalBranches: mapCriticalBranches(
      risks.slice(0, 3).map((r) => ({
        name: panelText(r.empresaCodigo ? `Filial ${r.empresaCodigo}` : null),
        metric: `${r.divergencias ?? 0} divergências`,
        tag: panelText(r.risco, "Risco"),
        view: "fiscalReconciliation",
      }))
    ),
    priorityActions: mapPriorityActions(alerts, { defaultView: "fiscalReconciliation" }),
    risks: mapRisks(
      risks.slice(0, 3).map((r) => ({
        title: `Filial ${panelText(r.empresaCodigo)}`,
        detail: `${r.divergencias ?? 0} divergências`,
        severity: r.risco,
      }))
    ),
    opportunities: [],
    alerts,
    detailHtml: detail,
    detailSummary: "Detalhamento fiscal",
  });

  node.querySelector("#nfceIntelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#nfceIntelExport")?.addEventListener("click", () => {
    downloadCsv("nfce-fiscal-riscos.csv", risks);
  });
  bindExecutiveNav(node, options.onNavigate);
}
