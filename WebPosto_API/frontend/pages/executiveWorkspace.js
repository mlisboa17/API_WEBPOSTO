import { buildExecutiveWorkspace } from "../services/workspaceEngine.js";

function renderSummaryCards(items = []) {
  return items
    .map(
      (card) => `
        <article class="ws-card ws-card--summary">
          <span class="ws-card__label">${card.label}</span>
          <strong class="ws-card__value">${card.value}</strong>
          <span class="ws-card__hint">${card.hint}</span>
        </article>
      `
    )
    .join("");
}

function renderAlerts(items = []) {
  if (!items.length) return `<p class="muted">Nenhum alerta crítico no período.</p>`;
  return items
    .slice(0, 8)
    .map(
      (alert) => `
        <article class="ws-alert ws-alert--${alert.severity.toLowerCase().replace("í", "i")}" data-nav-view="${alert.view}">
          <div class="ws-alert__head">
            <span class="ws-badge">${alert.severity}</span>
            <span class="ws-origin">${alert.origin}</span>
          </div>
          <strong>${alert.title}</strong>
          <p class="muted">${alert.detail}</p>
        </article>
      `
    )
    .join("");
}

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

function renderExecution(exe = {}) {
  return `
    <div class="ws-exec-grid">
      <article class="ws-card"><span class="ws-card__label">Ações abertas</span><strong>${exe.abertas ?? "—"}</strong></article>
      <article class="ws-card"><span class="ws-card__label">Executadas</span><strong>${exe.executadas ?? "—"}</strong></article>
      <article class="ws-card"><span class="ws-card__label">Validadas</span><strong>${exe.validadas ?? "—"}</strong></article>
      <article class="ws-card"><span class="ws-card__label">ROI realizado</span><strong>${exe.roi ?? "—"}</strong></article>
      <article class="ws-card"><span class="ws-card__label">Taxa execução</span><strong>${exe.taxaExecucao ?? "—"}${exe.taxaExecucao !== "—" ? "%" : ""}</strong></article>
    </div>
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
    node.innerHTML = `<p class="muted">Montando workspace executivo…</p>`;
    return;
  }

  const workspace = buildExecutiveWorkspace(data);
  const period = `${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}`;

  node.innerHTML = `
    <header class="view-header ws-header">
      <div>
        <h2>Home Executiva</h2>
        <p class="muted">Centro de decisão operacional · ${period}</p>
      </div>
      <div class="view-actions">
        <button type="button" id="workspaceRefresh" class="btn-secondary">Atualizar workspace</button>
      </div>
    </header>

    <section class="ws-block">
      <h3>Resumo da Rede</h3>
      <div class="ws-summary-grid">${renderSummaryCards(workspace.summary)}</div>
    </section>

    <div class="ws-grid-2">
      <section class="ws-block ws-block--alerts">
        <h3>Alert Center</h3>
        <div class="ws-alert-list">${renderAlerts(workspace.alerts)}</div>
      </section>
      <section class="ws-block ws-block--opps">
        <h3>Opportunity Center</h3>
        ${renderOpportunities(workspace.opportunities)}
      </section>
    </div>

    <section class="ws-block">
      <h3>Execução</h3>
      ${renderExecution(workspace.execution)}
    </section>

    <section class="ws-block">
      <h3>Branch Intelligence</h3>
      <div class="ws-branch-grid">
        <article><h4>Top filiais</h4>${renderBranchList("top", workspace.branches.top)}</article>
        <article><h4>Filiais em risco</h4>${renderBranchList("risco", workspace.branches.risk)}</article>
        <article><h4>Sem LMC</h4>${renderBranchList("LMC", workspace.branches.semLmc)}</article>
        <article><h4>Melhor mix</h4>${renderBranchList("mix", workspace.branches.bestMix)}</article>
        <article><h4>Dependência combustível</h4>${renderBranchList("comb", workspace.branches.fuelDependency)}</article>
      </div>
    </section>
  `;

  node.querySelector("#workspaceRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelectorAll("[data-nav-view]").forEach((el) => {
    el.addEventListener("click", () => {
      const view = el.getAttribute("data-nav-view");
      if (view) options.onNavigate?.(view);
    });
  });
}
