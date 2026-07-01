function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function barRows(rows, unit = "R$") {
  if (!rows.length) return `<p class="muted">Sem dados reais para este ranking.</p>`;
  const max = Math.max(...rows.map((row) => Number(row.value || 0)), 1);
  return `
    <div class="pres-bars">
      ${rows
        .map((row) => {
          const width = Math.max(6, (Number(row.value || 0) / max) * 100);
          return `
            <div class="pres-bar-row">
              <span>${escapeHtml(row.label)}</span>
              <div><i style="width:${width}%"></i></div>
              <strong>${unit === "%" ? `${Number(row.value || 0).toFixed(1)}%` : Number(row.value || 0).toLocaleString("pt-BR")}</strong>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function fuelRows(rows) {
  if (!rows.length) return `<p class="muted">Sem dados reais de combustiveis neste periodo.</p>`;
  return rows
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.label)}</td>
          <td>${item.value == null ? "Nao informado" : Number(item.value).toLocaleString("pt-BR")}</td>
          <td>${item.share == null ? "Sem proporcao" : `${item.share.toFixed(1)}%`}</td>
          <td>${item.margin == null ? "Nao informado" : Number(item.margin).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</td>
        </tr>
      `
    )
    .join("");
}

export function renderPresidentDashboard(node, data, filters, options = {}) {
  if (!node) return;
  if (!data) {
    node.innerHTML = `<section class="state">Carregando inteligencia executiva...</section>`;
    return;
  }

  const hasKpi = data.kpis.some((item) => item.raw != null);
  if (!hasKpi && !data.branchRanking.length && !data.fuelMix.length) {
    node.innerHTML = `
      <section class="pres-page">
        <header class="pres-hero">
          <div>
            <span>Presidente</span>
            <h2>Visao estrategica</h2>
            <p>Nenhum dado real retornou para o periodo selecionado.</p>
          </div>
          <button type="button" class="btn-secondary" id="presRefresh">Atualizar</button>
        </header>
      </section>
    `;
    node.querySelector("#presRefresh")?.addEventListener("click", () => options.onRefresh?.());
    return;
  }

  node.innerHTML = `
    <section class="pres-page">
      <header class="pres-hero">
        <div>
          <span>Presidente</span>
          <h2>Visao estrategica da rede</h2>
          <p>${escapeHtml(filters.dataInicial)} a ${escapeHtml(filters.dataFinal)} · dados reais WebPosto</p>
        </div>
        <button type="button" class="btn-secondary" id="presRefresh">Atualizar</button>
      </header>

      <section class="pres-kpis">
        ${data.kpis
          .map(
            (item) => `
              <article class="pres-kpi pres-kpi--${item.tone}">
                <span>${escapeHtml(item.label)}</span>
                <strong>${escapeHtml(item.value)}</strong>
                <em>${escapeHtml(item.delta)}</em>
              </article>
            `
          )
          .join("")}
      </section>

      <section class="pres-grid">
        <article class="pres-panel pres-panel--wide">
          <header><h3>Ranking de filiais</h3><span>Receita consolidada</span></header>
          ${barRows(data.branchRanking)}
        </article>

        <article class="pres-panel">
          <header><h3>Alertas executivos</h3><span>Prioridade de decisao</span></header>
          <div class="pres-alerts">
            ${
              data.alerts.length
                ? data.alerts
                    .map((alert) => `<div class="pres-alert pres-alert--${alert.tone}"><strong>${escapeHtml(alert.title)}</strong><p>${escapeHtml(alert.detail)}</p></div>`)
                    .join("")
                : `<p class="muted">Sem alertas criticos no recorte atual.</p>`
            }
          </div>
        </article>

        <article class="pres-panel">
          <header><h3>Mix de combustiveis</h3><span>Volume, proporcao e margem</span></header>
          <table class="data-table pres-table">
            <thead><tr><th>Produto</th><th>Volume</th><th>Mix</th><th>Margem</th></tr></thead>
            <tbody>${fuelRows(data.fuelMix)}</tbody>
          </table>
        </article>

        <article class="pres-panel">
          <header><h3>Insights automaticos</h3><span>Leitura executiva</span></header>
          <div class="pres-insights">
            ${
              data.insights.length
                ? data.insights.map((item) => `<p class="pres-insight pres-insight--${item.tone}">${escapeHtml(item.text)}</p>`).join("")
                : `<p class="muted">Sem insights suficientes com dados reais.</p>`
            }
          </div>
        </article>
      </section>
    </section>
  `;

  node.querySelector("#presRefresh")?.addEventListener("click", () => options.onRefresh?.());
}
