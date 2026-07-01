import { formatKpiTrend } from "../services/executiveKpis.js";



export function setViewTitle(title) {
  const titleHost = document.getElementById("viewTitleHost");
  if (titleHost && title) titleHost.innerHTML = `<h2>${title}</h2>`;
}

export function renderExecutiveEmptyState({
  title,
  message = "Dados indisponíveis para este período.",
  chartTitle = "Desempenho no período",
} = {}) {
  setViewTitle(title);
  const kpis = [
    { label: "Receita", value: "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Despesa", value: "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Margem", value: "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Alertas", value: "0", trendPct: null, status: "ok" },
  ];
  return `${renderExecutiveFirstFold({ title, kpis, chartBars: [], chartTitle, alerts: [] })}${wrapExecutiveDetail(
    `<div class="exec-empty-msg exec-empty-card"><strong class="exec-empty-card__title">Dados indisponíveis</strong><p>${message}</p></div>`,
    "Detalhamento"
  )}`;
}

export function companySubtitle(filters = {}, companies = []) {
  const raw = filters?.empresaCodigo;
  if (raw == null || raw === "" || raw === "all" || raw === "__all__") return "Todas as empresas";
  
  const values = Array.isArray(raw) ? raw.filter(Boolean) : [raw];
  if (!values.length) return "Todas as empresas";
  
  if (values.length === 1) {
    const code = String(values[0]);
    const found = companies.find(c => String(c.empresaCodigo) === code || String(c.codigo) === code);
    return found ? (found.filial || found.nome || code) : `Empresa ${code}`;
  }
  
  return `${values.length} empresas selecionadas`;
}

function statusClass(status) {
  if (status === "crit" || status === "critical") return "crit";
  if (status === "warn" || status === "warning") return "warn";
  return "ok";
}

function trendHint(status) {
  if (status === "crit") return "Ação necessária";
  if (status === "warn") return "Atenção";
  return "Estável";
}

export function renderKpiHero(kpis = []) {
  const tiles = (kpis.length ? kpis : []).slice(0, 4);
  while (tiles.length < 4) {
    tiles.push({ label: "—", value: "Dados indisponíveis", trendPct: null, status: "ok" });
  }
  return tiles
    .slice(0, 4)
    .map((kpi) => {
      const trend = formatKpiTrend(kpi.trendPct);
      const tone = statusClass(kpi.status);
      const isUnavailable = kpi.value === "—" || kpi.value === "Dados indisponíveis" || kpi.value === "Integração protegida";
      const displayValue = kpi.value === "Integração protegida" ? "Integração protegida" : (isUnavailable ? "Dados indisponíveis" : kpi.value);
      const hint = trend.text === "estável" ? trendHint(tone) : trend.text;
      
      let subtext = `${trend.arrow} ${hint}`;
      if (kpi.value === "Integração protegida") {
        subtext = "Consulte diagnóstico técnico";
      }
      
      return `
        <article class="exec-kpi-tile exec-kpi-tile--${tone} ${isUnavailable ? 'exec-kpi-tile--empty' : ''}">
          <div class="exec-kpi-tile__head">
            <span class="exec-kpi-tile__label">${kpi.label}</span>
            <span class="exec-kpi-tile__status" aria-hidden="true"></span>
          </div>
          <strong class="exec-kpi-tile__value">${displayValue}</strong>
          <span class="exec-kpi-tile__trend exec-kpi-tile__trend--${trend.cls}">
            ${subtext}
          </span>
        </article>
      `;
    })
    .join("");
}



export function renderExecutiveBrief(brief) {

  if (!brief) return "";

  const items = [

    { q: "O que aconteceu?", a: brief.what },

    { q: "Por que aconteceu?", a: brief.why },

    { q: "Onde aconteceu?", a: brief.where },

    { q: "O que fazer agora?", a: brief.actionNow },

  ];

  return `

    <section class="exec-brief exec-grid-12">

      <h3 class="exec-section-label">Leitura executiva</h3>

      <div class="exec-brief-grid">

        ${items

          .map(

            (item) => `

              <article class="exec-brief-item">

                <span class="exec-brief-item__q">${item.q}</span>

                <p class="exec-brief-item__a">${item.a}</p>

              </article>

            `

          )

          .join("")}

      </div>

    </section>

  `;

}



function renderDecisionList(items, emptyText, withNav = false) {

  if (!items?.length) {

    return `<li class="exec-decision-empty">${emptyText}</li>`;

  }

  return items

    .map((item) => {

      const nav = withNav && item.view ? ` data-nav-view="${item.view}"` : "";

      const actionBtn =

        withNav && item.view

          ? `<button type="button" class="exec-decision-action btn-link" data-nav-view="${item.view}">Agir →</button>`

          : "";

      return `

        <li class="exec-decision-item"${nav}>

          <strong>${item.title || item.name}</strong>

          ${item.metric ? `<span class="exec-decision-metric">${item.metric}</span>` : ""}

          ${item.detail ? `<small>${item.detail}</small>` : ""}

          ${item.impact ? `<small>${item.impact}</small>` : ""}

          ${item.tag ? `<em class="exec-decision-tag">${item.tag}</em>` : ""}

          ${actionBtn}

        </li>

      `;

    })

    .join("");

}



export function renderDecisionPanel({ criticalBranches = [], priorityActions = [], risks = [], opportunities = [] } = {}) {

  const hasContent =

    criticalBranches.length || priorityActions.length || risks.length || opportunities.length;

  if (!hasContent) return "";



  return `

    <section class="exec-decision-panel exec-grid-12">

      <div class="exec-decision-col">

        <h4 class="exec-decision-col__title">Filiais críticas</h4>

        <ul class="exec-decision-list">${renderDecisionList(criticalBranches, "Nenhuma filial crítica.", true)}</ul>

      </div>

      <div class="exec-decision-col">

        <h4 class="exec-decision-col__title">Ações prioritárias</h4>

        <ul class="exec-decision-list">${renderDecisionList(priorityActions, "Nenhuma ação pendente.", true)}</ul>

      </div>

      <div class="exec-decision-col">

        <h4 class="exec-decision-col__title">Riscos</h4>

        <ul class="exec-decision-list">${renderDecisionList(

          risks.map((r) => ({ title: r.title, detail: r.detail, tag: r.severity })),

          "Sem riscos prioritários."

        )}</ul>

      </div>

      <div class="exec-decision-col">

        <h4 class="exec-decision-col__title">Oportunidades</h4>

        <ul class="exec-decision-list">${renderDecisionList(

          opportunities.map((o) => ({ title: o.title, detail: o.impact, view: o.view })),

          "Sem oportunidades mapeadas.",

          true

        )}</ul>

      </div>

    </section>

  `;

}



export function renderChartHero(bars = [], title = "Desempenho no período") {

  if (!bars.length) {

    return `

      <div class="exec-chart-hero__inner">

        <h3 class="exec-chart-hero__title">${title}</h3>

        <p class="muted exec-chart-hero__empty">Sem dados para exibir neste período.</p>

      </div>

    `;

  }

  const maxVal = Math.max(...bars.map((b) => b.value), 1);

  return `

    <div class="exec-chart-hero__inner">

      <h3 class="exec-chart-hero__title">${title}</h3>

      <div class="exec-chart-bars" role="img" aria-label="${title}">

        ${bars

          .map(

            (bar) => `

              <div class="exec-chart-bar exec-chart-bar--${bar.tone || "neutral"}">

                <div class="exec-chart-bar__fill" style="height:${Math.max(8, Math.round((bar.value / maxVal) * 100))}%"></div>

                <span class="exec-chart-bar__label">${bar.label}</span>

              </div>

            `

          )

          .join("")}

      </div>

    </div>

  `;

}



export function renderPriorityAlerts(alerts = [], options = {}) {
  const max = options.max ?? 3;
  const items = (alerts || []).slice(0, max);

  if (!items.length) {
    return `<p class="muted exec-alerts__empty">Nenhum alerta prioritário no período.</p>`;
  }

  return items
    .map((alert) => {
      const sev = String(alert.severity || "MÉDIO").toUpperCase();
      const tone =
        sev.includes("CRIT") || sev === "ALTA" || sev === "HIGH"
          ? "crit"
          : sev.includes("ALTO") || sev === "MÉDIO"
            ? "warn"
            : "ok";

      const badge =
        tone === "crit" ? "Crítico" : tone === "warn" ? "Atenção" : "Informação";

      return `
        <article class="exec-alert exec-alert--${tone}" ${alert.view ? `data-nav-view="${alert.view}"` : ""}>
          <div class="exec-alert__head">
            <span class="exec-alert__badge">${badge}</span>
            ${alert.origin ? `<span class="exec-alert__origin">${alert.origin}</span>` : ""}
          </div>
          <div class="exec-alert__body">
            ${alert.title ? `<p class="exec-alert__why"><span>Problema:</span> ${alert.title}</p>` : ""}
            ${[alert.why, alert.where, alert.detail].filter(Boolean).length ? `<p class="exec-alert__where"><span>Impacto:</span> ${[alert.why, alert.where, alert.detail].filter(Boolean).join(" · ")}</p>` : ""}
            ${alert.actionNow ? `<p class="exec-alert__action-text"><span>Ação:</span> ${alert.actionNow}</p>` : ""}
          </div>
          ${alert.view ? `<button type="button" class="exec-alert__action btn-link" data-nav-view="${alert.view}">Agir →</button>` : ""}
        </article>
      `;
    })
    .join("");
}



/** RT-07.3.1 — 1ª dobra: KPIs → Alertas → Gráfico */
export function renderExecutiveFirstFold({
  title,
  kpis,
  chartBars,
  chartTitle,
  alerts,
}) {
  setViewTitle(title);

  return `
    <section class="exec-first-fold exec-first-fold--premium">
      <div class="exec-kpi-grid exec-grid-12">${renderKpiHero(kpis)}</div>

      <div class="exec-alerts exec-grid-12">
        <h3 class="exec-section-label">Alertas prioritários</h3>
        <div class="exec-alerts__list">${renderPriorityAlerts(alerts, { max: 3 })}</div>
      </div>

      <div class="exec-hero-row exec-grid-12">
        <div class="exec-chart-hero exec-col-12">${renderChartHero(chartBars, chartTitle)}</div>
      </div>
    </section>
  `;
}



export function wrapExecutiveDetail(content, summary = "Detalhamento") {

  return `

    <details class="exec-detail-fold">

      <summary class="exec-detail-fold__summary">${summary}</summary>

      <div class="exec-detail-fold__body">${content}</div>

    </details>

  `;

}



export function bindExecutiveNav(node, onNavigate) {

  if (!node || !onNavigate) return;

  node.querySelectorAll("[data-nav-view]").forEach((el) => {

    el.addEventListener("click", () => {

      const view = el.getAttribute("data-nav-view");

      if (view) onNavigate(view);

    });

  });

}

