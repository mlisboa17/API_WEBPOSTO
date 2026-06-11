import { downloadCsv } from "../services/export.js";

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .filter(Boolean)
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          return `<td>${val ?? "—"}</td>`;
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
    <article class="panel copilot-answer">
      <p><strong>${item.tipo || "—"}</strong></p>
      <p class="muted">Valor: ${item.valor ?? "—"} · Severidade: ${item.severidade ?? "—"}</p>
    </article>
  `
    )
    .join("");
  return `<section class="panel"><h3>Top Ocorrências</h3>${cards}</section>`;
}

export function renderNfceIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando NFCE Intelligence…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const recon = payload.nfceReconciliationEngine || cockpit.reconciliacao || {};
  const risks = payload.nfceRiskEngine?.risks || cockpit.riscoFiscal || [];
  const patterns = payload.nfceAnomalyEngine?.patterns || cockpit.topOcorrencias || [];
  const execIntel = payload.nfceExecutiveIntelligence || cockpit.executiveIntelligence || {};
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>NFCE Intelligence</h2>
        <p class="muted">F06.1 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="nfceIntelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="nfceIntelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">NFCE Emitidas</span><strong>${exec["2_emitidas"] ?? cockpit.nfceEmitidas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Canceladas</span><strong>${exec["3_canceladas"] ?? cockpit.nfceCanceladas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Inutilizadas</span><strong>${exec["4_inutilizadas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Pendentes</span><strong>${exec["5_pendentes"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Cobertura Reconc.</span><strong>${exec["6_coberturaReconciliacao"] ?? recon.coveragePct ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Divergências</span><strong>${exec["8_divergencias"] ?? cockpit.divergencias ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Risco Máximo</span><strong>${exec["9_riscoMaximo"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Filial Maior Risco</span><strong>${exec["10_filialMaiorRisco"] ?? execIntel.filialMaiorRisco?.empresaCodigo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F06.2</span><strong>${exec["20_aprovadoF062"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderPatterns(patterns)}
    ${renderTable("Risco Fiscal por Filial", risks, [
      { key: "empresaCodigo", label: "Filial" },
      { key: "risco", label: "Risco" },
      { key: "cancelamentos", label: "Cancelamentos" },
      { key: "ausencias", label: "Ausências" },
      { key: "divergencias", label: "Divergências" },
    ])}
    ${renderTable("Reconciliação", recon.items || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Quantidade" },
    ])}
  `;

  node.querySelector("#nfceIntelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#nfceIntelExport")?.addEventListener("click", () => {
    downloadCsv("nfce-intelligence-risks.csv", risks);
  });
}
