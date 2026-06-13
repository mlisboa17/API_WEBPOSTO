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

export function renderCommercialLearning(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Aprendizado Comercial…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const effectiveness = payload.recommendationEffectivenessEngine || {};
  const responsible = payload.responsiblePerformanceEngine || {};
  const branch = payload.branchLearningEngine || {};
  const calibration = payload.recommendationCalibrationEngine || {};
  const outcome = payload.outcomeLearningEngine || {};
  const execReport = payload.executiveLearningReport || {};
  const tipos = effectiveness.porTipo || cockpit.melhoresAcoes || [];
  const owners = responsible.porResponsavel || cockpit.melhoresResponsaveis || [];
  const filiais = branch.porFilial || cockpit.melhoresFiliais || [];
  const calibrations = calibration.calibrations || cockpit.calibrations || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Aprendizado Comercial Produtos Vendidos</h2>
        <p class="muted">F07.8 · Calibração · Efetividade · ROI Previsto vs Real · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="commercialLearningRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="commercialLearningExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Ações avaliadas</span><strong>${exec["1_acoesAvaliadas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Validadas</span><strong>${exec["3_acoesValidadas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI previsto</span><strong>R$ ${exec["14_roiPrevisto"] ?? cockpit.roiPrevisto ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI realizado</span><strong>R$ ${exec["15_roiRealizado"] ?? cockpit.roiRealizado ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Taxa acerto</span><strong>${exec["16_taxaAcertoPct"] ?? cockpit.taxaAcertoPct ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Sistema aprendeu</span><strong>${exec["17_sistemaAprendeu"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Calibradas</span><strong>${calibration.totalCalibradas ?? calibrations.length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F07.9</span><strong>${exec["20_aprovadoF079"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Efetividade por tipo de ação", tipos.slice(0, 10), [
      { key: "tipo", label: "Tipo" },
      { key: "validadas", label: "Validadas" },
      { key: "roiReal", label: "ROI real", render: (r) => `R$ ${r.roiReal ?? "—"}` },
      { key: "taxaAcertoPct", label: "Taxa acerto", render: (r) => `${r.taxaAcertoPct ?? "—"}%` },
    ])}
    ${renderTable("Calibração ROI previsto vs real", calibrations.slice(0, 10), [
      { key: "actionId", label: "Ação" },
      { key: "tipo", label: "Tipo" },
      { key: "roiPrevisto", label: "Previsto", render: (r) => `R$ ${r.roiPrevisto ?? "—"}` },
      { key: "roiReal", label: "Real", render: (r) => `R$ ${r.roiReal ?? "—"}` },
      { key: "erroPct", label: "Erro %", render: (r) => `${r.erroPct ?? "—"}%` },
      { key: "confidenceLevel", label: "Confiança" },
    ])}
    ${renderTable("Melhores responsáveis", owners.slice(0, 8), [
      { key: "responsavel", label: "Responsável" },
      { key: "acoesValidadas", label: "Validadas" },
      { key: "receitaGerada", label: "Receita", render: (r) => `R$ ${r.receitaGerada ?? "—"}` },
      { key: "roiMedio", label: "ROI médio", render: (r) => `R$ ${r.roiMedio ?? "—"}` },
    ])}
    ${renderTable("Aprendizado por filial", filiais.slice(0, 8), [
      { key: "empresaCodigo", label: "Filial" },
      { key: "taxaExecucaoPct", label: "Execução %", render: (r) => `${r.taxaExecucaoPct ?? "—"}%` },
      { key: "taxaValidacaoPct", label: "Validação %", render: (r) => `${r.taxaValidacaoPct ?? "—"}%` },
      { key: "roiReal", label: "ROI real", render: (r) => `R$ ${r.roiReal ?? "—"}` },
    ])}
    <section class="panel">
      <h3>Outcome Learning</h3>
      <p class="muted">Melhor ação resultado: <strong>${execReport.melhorAcaoResultado ?? exec["6_melhorAcao"] ?? "—"}</strong> · Pior: <strong>${execReport.piorAcao ?? exec["7_piorAcao"] ?? "—"}</strong></p>
      <p class="muted">Erro médio receita: R$ ${outcome.erroMedioReceita ?? "—"} · Melhora temporal: ${outcome.melhoraAoLongoDoTempoPct ?? "—"}%</p>
    </section>
  `;

  node.querySelector("#commercialLearningRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#commercialLearningExport")?.addEventListener("click", () => {
    downloadCsv("commercial_learning.csv", calibrations, [
      "actionId",
      "tipo",
      "empresaCodigo",
      "roiPrevisto",
      "roiReal",
      "erroPct",
      "confidenceLevel",
    ]);
  });
}
