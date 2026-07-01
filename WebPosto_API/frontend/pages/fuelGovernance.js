import { downloadCsv } from "../services/export.js";
import { getNomeFilial } from "../components/filiais.js";
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

const FUEL_EMPTY_MSG = "Integração protegida ou sem movimentação no período.";

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

export function renderFuelGovernance(node, payload, filters, options = {}) {
  if (!node) return;

  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Governança",
      message: FUEL_EMPTY_MSG,
      chartTitle: "Conformidade por filial",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const ranking = payload.branchComplianceRanking?.ranking || cockpit.rankingFiliais || [];
  const delays = payload.delayAnalysisEngine?.atrasos || cockpit.atrasos || [];
  const parecer = payload.parecerFinal || "";
  const hasData = ranking.length > 0 || delays.length > 0;

  if (!hasData) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Governança",
      message: FUEL_EMPTY_MSG,
      chartTitle: "Conformidade por filial",
    });
    return;
  }
  const conformidadeMedia =
    ranking.length > 0
      ? Math.round(ranking.reduce((sum, row) => sum + Number(row.conformidadePct || 0), 0) / ranking.length)
      : null;
  const filiaisRisco = ranking.filter((r) => Number(r.conformidadePct || 100) < 80).length;
  const atrasosCount = delays.length;

  const kpis = [
    {
      label: "Conformidade",
      value: conformidadeMedia != null ? `${conformidadeMedia}%` : "Dados indisponíveis",
      trendPct: null,
      status: conformidadeMedia != null && conformidadeMedia < 80 ? "warn" : "ok",
    },
    {
      label: "Filiais em risco",
      value: hasData ? countKpi(filiaisRisco) : "Dados indisponíveis",
      trendPct: null,
      status: filiaisRisco > 0 ? "crit" : "ok",
    },
    {
      label: "Atrasos",
      value: hasData ? countKpi(atrasosCount) : "Dados indisponíveis",
      trendPct: null,
      status: atrasosCount > 0 ? "warn" : "ok",
    },
    {
      label: "Alertas",
      value: String(Math.min(3, filiaisRisco + atrasosCount) || 0),
      trendPct: null,
      status: filiaisRisco + atrasosCount > 0 ? "crit" : "ok",
    },
  ];

  const worstBranch = [...ranking].sort(
    (a, b) => Number(a.conformidadePct || 100) - Number(b.conformidadePct || 100)
  )[0];
  const topDelay = delays[0];

  const brief = buildFourQuestionBrief({
    what:
      conformidadeMedia != null
        ? `Conformidade média da rede: ${conformidadeMedia}%.`
        : "Governança operacional em consolidação.",
    why:
      atrasosCount > 0
        ? `${atrasosCount} pendência(s) de registro operacional.`
        : filiaisRisco > 0
          ? `${filiaisRisco} filial(is) abaixo de 80% de conformidade.`
          : "Rotina operacional dentro do esperado.",
    where: worstBranch
      ? getNomeFilial(worstBranch.empresaCodigo)
      : topDelay
        ? getNomeFilial(topDelay.empresaCodigo)
        : "Rede consolidada",
    actionNow: topDelay
      ? `Regularizar registro em ${getNomeFilial(topDelay.empresaCodigo)} hoje.`
      : worstBranch
        ? `Reforçar disciplina em ${getNomeFilial(worstBranch.empresaCodigo)}.`
        : "Manter rotina de fechamento diário.",
  });

  const chartBars = buildChartBars(ranking.slice(0, 7), {
    labelKey: "nomeFilial",
    valueKey: "conformidadePct",
    max: 7,
  });

  const alerts = [];
  delays.slice(0, 3).forEach((row) => {
    alerts.push(
      enrichAlert(
        {
          severity: "ALTO",
          title: `Registro pendente — ${getNomeFilial(row.empresaCodigo)}`,
          detail: row.atrasoDias != null || row.diasAtraso != null ? `${row.atrasoDias ?? row.diasAtraso} dia(s)` : "Não informado",
          view: "fuelGovernance",
          origin: "Governança",
        },
        {
          why: row.tipo || "Pendência operacional",
          where: getNomeFilial(row.empresaCodigo),
          actionNow: "Completar registro do período",
        }
      )
    );
  });
  ranking
    .filter((r) => Number(r.conformidadePct || 100) < 80)
    .slice(0, 3 - alerts.length)
    .forEach((row) => {
      alerts.push(
        enrichAlert(
          {
            severity: "ALTO",
            title: `Conformidade baixa — ${getNomeFilial(row.empresaCodigo)}`,
            detail: row.conformidadePct != null ? `${row.conformidadePct}%` : "Não informado",
            view: "fuelGovernance",
            origin: "Governança",
          },
          {
            why: "Abaixo do patamar mínimo de 80%",
            where: getNomeFilial(row.empresaCodigo),
            actionNow: "Revisar fechamentos e registros",
          }
        )
      );
    });

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="fuelGovRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="fuelGovExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
    ${renderTable("Desempenho por filial", ranking, [
      { key: "rank", label: "#" },
      { key: "empresaCodigo", label: "Filial", render: (r) => getNomeFilial(r.empresaCodigo) },
      { key: "nomeFilial", label: "Nome" },
      { key: "conformidadePct", label: "Conformidade %", render: (r) => (r.conformidadePct != null ? `${r.conformidadePct}%` : null) },
      { key: "disciplina", label: "Disciplina" },
      {
        key: "preenchidoPor",
        label: "Responsável",
        render: (r) => (Array.isArray(r.preenchidoPor) ? r.preenchidoPor.join(", ") : r.preenchidoPor),
      },
    ])}
    ${renderTable("Pendências operacionais", delays.slice(0, 10), [
      { key: "dataMovimento", label: "Data", render: (r) => r.dataMovimento || r.data },
      { key: "tipo", label: "Tipo" },
      { key: "atrasoDias", label: "Atraso (dias)" },
      { key: "preenchidoPor", label: "Operador" },
      { key: "empresaCodigo", label: "Filial", render: (r) => getNomeFilial(r.empresaCodigo) },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Governança",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Conformidade por filial",
    criticalBranches: mapCriticalBranches(
      ranking
        .slice()
        .sort((a, b) => Number(a.conformidadePct || 100) - Number(b.conformidadePct || 100))
        .slice(0, 3)
        .map((row) => ({
          name: getNomeFilial(row.empresaCodigo),
          metric: row.conformidadePct != null ? `${row.conformidadePct}%` : "Não informado",
          tag: "Conformidade",
          view: "fuelGovernance",
        }))
    ),
    priorityActions: mapPriorityActions(
      alerts.slice(0, 3).map((a) => ({ title: a.title, detail: a.actionNow, view: a.view }))
    ),
    risks: mapRisks(
      alerts.slice(0, 3).map((a) => ({ title: a.title, detail: a.why, severity: a.severity }))
    ),
    opportunities: [],
    alerts: alerts.slice(0, 3),
    detailHtml: detail,
    detailSummary: "Detalhamento de governança",
  });

  bindExecutiveNav(node, options.onNavigate);
  node.querySelector("#fuelGovRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#fuelGovExport")?.addEventListener("click", () => {
    downloadCsv("governanca-combustiveis.csv", ranking);
  });
}
