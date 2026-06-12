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

export function renderFuelGovernance(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Fuel Governance…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const ranking = payload.branchComplianceRanking?.ranking || cockpit.rankingFiliais || [];
  const delays = payload.delayAnalysisEngine?.atrasos || cockpit.atrasos || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Fuel Governance</h2>
        <p class="muted">F06.5 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""} · Governança operacional (sem fraude/perda presumida)</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="fuelGovRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="fuelGovExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Conformidade LMC</span><strong>${cockpit.conformidadeLmc || exec["3_taxaConformidadeLmc"]}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Dias com LMC</span><strong>${exec["1_diasComLmc"] ?? cockpit.diasComLmc ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Dias sem LMC</span><strong>${exec["2_diasSemLmc"] ?? cockpit.diasSemLmc ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Periodicidade</span><strong>${cockpit.periodicidade ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Média atraso</span><strong>${exec["7_mediaAtrasoDias"] ?? cockpit.mediaAtrasoDias ?? "—"} d</strong></article>
      <article class="kpi-card"><span class="kpi-label">Retroativo</span><strong>${exec["11_preenchimentoRetroativo"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Problema principal</span><strong>${payload.fuelGovernanceIntelligence?.problemaPrincipal ?? cockpit.governancaCombustivel ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F06.6</span><strong>${exec["20_aprovadoF066"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Ranking filiais", ranking, [
      { key: "rank", label: "#" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "nomeFilial", label: "Nome" },
      { key: "conformidadePct", label: "Conformidade %" },
      { key: "disciplina", label: "Disciplina" },
      { key: "preenchidoPor", label: "Preenche", render: (r) => (Array.isArray(r.preenchidoPor) ? r.preenchidoPor.join(", ") : r.preenchidoPor) },
    ])}
    ${renderTable("Atrasos / lacunas", delays.slice(0, 10), [
      { key: "dataMovimento", label: "Data LMC", render: (r) => r.dataMovimento || r.data },
      { key: "tipo", label: "Tipo" },
      { key: "atrasoDias", label: "Atraso (d)" },
      { key: "preenchidoPor", label: "Operador" },
      { key: "empresaCodigo", label: "Filial" },
    ])}
  `;

  node.querySelector("#fuelGovRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#fuelGovExport")?.addEventListener("click", () => {
    downloadCsv("fuel-governance-ranking.csv", ranking);
  });
}
