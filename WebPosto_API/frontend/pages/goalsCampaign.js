import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function opLabel(item) {
  if (!item) return "—";
  return item.employeeName ? `${item.employeeName} (${item.funcionarioCodigo})` : String(item.funcionarioCodigo ?? "—");
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          if (c.money) return `<td>${fmtMoney(val)}</td>`;
          return `<td>${val ?? "—"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderGoalsCampaign(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Goals & Campaigns…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const qa = payload.qa || {};
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Goals & Campaigns</h2>
        <p class="muted">F04.5 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="goalsRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="goalsExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Metas Criadas</span><strong>${exec["1_metasCriadas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Campanhas</span><strong>${exec["2_campanhasSimuladas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Bateram Meta</span><strong>${exec["3_bateramMeta"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Abaixo Meta</span><strong>${exec["4_abaixoMeta"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Bônus Elegíveis</span><strong>${exec["6_merecemBonus"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Alertas</span><strong>${exec["13_alertasGerados"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Impacto Financeiro</span><strong>${fmtMoney(exec["14_impactoFinanceiroEsperado"])}</strong></article>
    </div>
    ${renderTable("Metas Ativas", cockpit.metasAtivas, [
      { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
      { key: "goalType", label: "Tipo" },
      { key: "targetValue", label: "Meta", money: true },
    ])}
    ${renderTable("Campanhas", cockpit.campanhas, [
      { key: "name", label: "Campanha" },
      { key: "status", label: "Status" },
      { key: "percentualMedio", label: "% Médio" },
      { key: "roiCampanha", label: "ROI", money: true },
    ])}
    ${renderTable("Ranking Operadores", cockpit.ranking, [
      { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
      { key: "goalType", label: "Meta" },
      { key: "percentualAtingido", label: "% Atingido" },
      { key: "status", label: "Status" },
    ])}
    ${renderTable("Bônus Projetado", cockpit.bonusProjetado, [
      { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
      { key: "elegivel", label: "Elegível", render: (r) => (r.elegivel ? "Sim" : "Não") },
      { key: "bonusSugerido", label: "Valor", money: true },
      { key: "roiEsperado", label: "ROI Esp.", money: true },
    ])}
    ${renderTable("Operadores Abaixo da Meta", cockpit.operadoresAbaixoMeta, [
      { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
      { key: "goalType", label: "Meta" },
      { key: "percentualAtingido", label: "%" },
      { key: "gap", label: "Gap", money: true },
    ])}
    ${renderTable("Alertas", cockpit.alertas, [
      { key: "tipo", label: "Tipo" },
      { key: "operador", label: "Operador" },
      { key: "pct", label: "%" },
    ])}
    <p class="muted">QA evidência: ${qa.evidenciaCompleta ? "100%" : "Pendente"} · RBAC: ${qa.rbacAplicado ? "OK" : "—"}</p>`;

  node.querySelector("#goalsRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#goalsExport")?.addEventListener("click", () => {
    downloadCsv(cockpit.ranking || [], `goals_campaign_${filters?.dataInicial}_${filters?.dataFinal}`);
  });
}
