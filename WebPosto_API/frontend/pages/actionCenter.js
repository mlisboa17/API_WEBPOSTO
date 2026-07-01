import { formatCurrency } from "../services/format.js";
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

function cellText(value) {
  if (value == null || value === "" || value === "—") return "Não informado";
  return value;
}

function fmtMoney(v) {
  if (v == null || v === "") return "Dados indisponíveis";
  return formatCurrency(v);
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
          if (c.money) return `<td>${fmtMoney(val)}</td>`;
          return `<td>${cellText(val)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderActionCenter(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Alertas",
      message: "Não foi possível montar esta visão no período selecionado.",
      chartTitle: "Alertas por prioridade",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const prioridade1 = cockpit.prioridade1 || [];
  const vencidas = cockpit.vencidas || [];
  const semEvidencia = cockpit.semEvidencia || [];
  const alertas = [...prioridade1, ...vencidas].slice(0, 20);
  const hasData = alertas.length > 0 || semEvidencia.length > 0;

  if (!hasData) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Alertas",
      message: "Nenhum alerta prioritário no período.",
      chartTitle: "Alertas por prioridade",
    });
    return;
  }

  const kpis = [
    { label: "Prioridade alta", value: countKpi(prioridade1.length), trendPct: null, status: prioridade1.length ? "crit" : "ok" },
    { label: "Vencidas", value: countKpi(vencidas.length), trendPct: null, status: vencidas.length ? "warn" : "ok" },
    { label: "Sem evidência", value: countKpi(semEvidencia.length), trendPct: null, status: semEvidencia.length ? "warn" : "ok" },
    { label: "Alertas", value: String(Math.min(3, prioridade1.length + vencidas.length)), trendPct: null, status: "crit" },
  ];

  const top = prioridade1[0] || vencidas[0];
  const brief = buildFourQuestionBrief({
    what: `${prioridade1.length} ação(ões) prioritária(s) e ${vencidas.length} vencida(s).`,
    why: top ? cellText(top.acao || top.titulo) : "Fila de alertas em consolidação.",
    where: top?.empresaCodigo ? `Filial ${top.empresaCodigo}` : "Rede consolidada",
    actionNow: top ? `Executar: ${cellText(top.acao || top.titulo)}` : "Manter monitoramento.",
  });

  const chartBars = buildChartBars(
    [
      { label: "Prioridade", valor: prioridade1.length },
      { label: "Vencidas", valor: vencidas.length },
      { label: "Sem evidência", valor: semEvidencia.length },
    ],
    { labelKey: "label", valueKey: "valor", max: 3 }
  );

  const cards = prioridade1.slice(0, 3).map((row) =>
    enrichAlert(
      {
        severity: "ALTO",
        title: cellText(row.acao || row.titulo, "Ação prioritária"),
        detail: cellText(row.ownerName),
        view: "actionCenter",
        origin: "Operação",
      },
      {
        why: cellText(row.lifecycleStatus, "Pendente de execução"),
        where: row.empresaCodigo ? `Filial ${row.empresaCodigo}` : "Rede",
        actionNow: "Executar e registrar evidência",
      }
    )
  );

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="actionCenterRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="actionCenterExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${payload.parecerFinal ? `<p class="parecer">${payload.parecerFinal}</p>` : ""}
    ${renderTable("Ações prioritárias", prioridade1, [
      { key: "lifecycleStatus", label: "Status" },
      { key: "acao", label: "Ação" },
      { key: "ownerName", label: "Responsável" },
      { key: "roiEsperado", label: "ROI previsto", money: true },
      { key: "decisionEvidenceType", label: "Evidência" },
    ])}
    ${renderTable("Ações vencidas", vencidas, [
      { key: "acao", label: "Ação" },
      { key: "ownerName", label: "Responsável" },
      { key: "lifecycleStatus", label: "Status" },
      { key: "escalationReasons", label: "Motivos", render: (r) => (r.escalationReasons || []).join(", ") || null },
    ])}
    ${renderTable("Por responsável", cockpit.acoesPorResponsavel, [
      { key: "ownerName", label: "Responsável" },
      { key: "total", label: "Ações" },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Alertas",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Distribuição de alertas",
    criticalBranches: mapCriticalBranches(
      prioridade1.slice(0, 3).map((row) => ({
        name: cellText(row.ownerName, "Responsável"),
        metric: cellText(row.acao || row.titulo),
        tag: "Prioridade",
        view: "actionCenter",
      }))
    ),
    priorityActions: mapPriorityActions(
      cards.map((a) => ({ title: a.title, detail: a.actionNow, view: a.view }))
    ),
    risks: mapRisks(
      vencidas.slice(0, 3).map((r) => ({
        title: cellText(r.acao, "Ação vencida"),
        detail: cellText(r.ownerName),
        severity: "ALTO",
      }))
    ),
    opportunities: [],
    alerts: cards,
    detailHtml: detail,
    detailSummary: "Detalhamento de alertas",
  });

  bindExecutiveNav(node, options.onNavigate);
  node.querySelector("#actionCenterRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#actionCenterExport")?.addEventListener("click", () => {
    downloadCsv("alertas-prioritarios.csv", prioridade1);
  });
}
