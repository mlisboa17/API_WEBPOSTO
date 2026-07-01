import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";
import { bindExecutiveNav, renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi, moneyKpi } from "../services/executiveKpis.js";
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

function label(item, nameKey = "employeeName", codeKey = "funcionarioCodigo") {
  if (!item) return "Não informado";
  const name = item[nameKey] || item.nomeFilial || item.nome;
  const code = item[codeKey] ?? item.empresaCodigo ?? item.pdvCodigo ?? item.turno;
  return name ? `${name} (${code})` : cellText(code);
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

export function renderExecutiveScorecard(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Indicadores",
      message: "Não foi possível montar esta visão no período selecionado.",
      chartTitle: "Indicadores por filial",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const topFiliais = cockpit.topFiliais || [];
  const topOperadores = cockpit.topOperadores || [];
  const alertas = cockpit.alertas || [];
  const tendencias = cockpit.tendencias || {};
  const hasData = topFiliais.length > 0 || topOperadores.length > 0 || alertas.length > 0;

  if (!hasData) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Indicadores",
      message: "Nenhum indicador disponível no período.",
      chartTitle: "Indicadores por filial",
    });
    return;
  }

  const receitaTop = topFiliais.reduce((sum, f) => sum + Number(f.receita || 0), 0);
  const kpis = [
    { label: "Filiais", value: countKpi(topFiliais.length), trendPct: null, status: "ok" },
    { label: "Operadores", value: countKpi(topOperadores.length), trendPct: null, status: "ok" },
    { label: "Receita top", value: receitaTop > 0 ? moneyKpi(receitaTop) : "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Alertas", value: String(alertas.length), trendPct: null, status: alertas.length ? "warn" : "ok" },
  ];

  const topFilial = topFiliais[0];
  const topOp = topOperadores[0];
  const brief = buildFourQuestionBrief({
    what: `${topFiliais.length} filial(is) e ${topOperadores.length} operador(es) no ranking.`,
    why: topFilial ? `${cellText(topFilial.nomeFilial)} lidera receita.` : "Ranking em consolidação.",
    where: topFilial ? cellText(topFilial.nomeFilial) : "Rede",
    actionNow: topOp ? `Reconhecer desempenho de ${label(topOp)}.` : "Acompanhar evolução semanal.",
  });

  const chartBars = buildChartBars(topFiliais.slice(0, 7), {
    labelKey: "nomeFilial",
    valueKey: "receita",
    max: 7,
  });

  const cards = alertas.slice(0, 3).map((a) =>
    enrichAlert(
      {
        severity: a.severity || "MÉDIO",
        title: cellText(a.message || a.category, "Alerta executivo"),
        detail: cellText(a.category),
        view: "executiveScorecard",
        origin: "Executivo",
      },
      {
        why: cellText(a.category, "Indicador fora do padrão"),
        where: "Rede",
        actionNow: "Revisar indicador e definir ação",
      }
    )
  );

  const tendenciaRows = Object.entries(tendencias).map(([chave, valor]) => ({
    indicador: chave.replace(/_/g, " "),
    valor: valor == null ? "Não informado" : typeof valor === "object" ? "Ver detalhamento" : String(valor),
  }));

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="scorecardRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="scorecardExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${payload.parecerFinal ? `<p class="parecer">${payload.parecerFinal}</p>` : ""}
    ${renderTable("Top filiais", topFiliais, [
      { key: "nomeFilial", label: "Filial" },
      { key: "receita", label: "Receita", money: true },
    ])}
    ${renderTable("Top operadores", topOperadores, [
      { key: "employeeName", label: "Operador", render: (r) => label(r) },
      { key: "benchmarkScore", label: "Pontuação" },
    ])}
    ${renderTable("Alertas executivos", alertas, [
      { key: "severity", label: "Prioridade" },
      { key: "category", label: "Categoria" },
      { key: "message", label: "Mensagem" },
    ])}
    ${renderTable("Tendências", tendenciaRows, [
      { key: "indicador", label: "Indicador" },
      { key: "valor", label: "Situação" },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Indicadores",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Receita por filial",
    criticalBranches: mapCriticalBranches(
      topFiliais.slice(0, 3).map((f) => ({
        name: cellText(f.nomeFilial),
        metric: fmtMoney(f.receita),
        tag: "Receita",
        view: "executiveScorecard",
      }))
    ),
    priorityActions: mapPriorityActions(
      cards.map((a) => ({ title: a.title, detail: a.actionNow, view: a.view }))
    ),
    risks: mapRisks(
      alertas.slice(0, 3).map((a) => ({
        title: cellText(a.message),
        detail: cellText(a.category),
        severity: a.severity,
      }))
    ),
    opportunities: [],
    alerts: cards,
    detailHtml: detail,
    detailSummary: "Detalhamento de indicadores",
  });

  bindExecutiveNav(node, options.onNavigate);
  node.querySelector("#scorecardRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#scorecardExport")?.addEventListener("click", () => {
    downloadCsv("indicadores-executivos.csv", topOperadores);
  });
}
