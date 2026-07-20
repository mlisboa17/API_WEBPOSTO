import { LICENSED_COMPANIES } from "../config/managementScope.js";
import { formatPeriodBr } from "../services/format.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function branchRows(rows) {
  if (!rows.length) {
    return `<p class="pres-empty">Ainda não há dados confiáveis por unidade neste período.</p>`;
  }
  const visible = rows.slice(0, 4);
  const max = Math.max(...visible.map((row) => Number(row.value || 0)), 1);
  return visible.map((row, index) => `
    <div class="pres-branch-row">
      <span class="pres-branch-position">${index + 1}</span>
      <div class="pres-branch-main">
        <strong>${escapeHtml(row.label)}</strong>
        <div class="pres-branch-track"><i style="width:${Math.max(4, (Number(row.value || 0) / max) * 100)}%"></i></div>
      </div>
      <strong class="pres-branch-value">${row.available === false || row.value == null ? "Dados indisponíveis" : Number(row.value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</strong>
    </div>
  `).join("");
}

function decisionItems(data) {
  const alerts = data.alerts || [];
  if (alerts.length) {
    return alerts.slice(0, 3).map((item) => `
      <div class="pres-decision pres-decision--${item.tone}">
        <span>${item.tone === "bad" ? "Ação imediata" : "Acompanhar"}</span>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.detail)}</p>
      </div>
    `).join("");
  }
  const insight = data.insights?.[0];
  return `
    <div class="pres-decision pres-decision--good">
      <span>Leitura do período</span>
      <strong>Nenhuma ocorrência crítica calculada</strong>
      <p>${escapeHtml(insight?.text || "Confira a cobertura dos dados antes de concluir o fechamento.")}</p>
    </div>
  `;
}

function departmentCards(departments = []) {
  return departments.map((item) => `
    <article class="pres-department pres-department--${item.status}">
      <header>
        <span>${item.status === "available" ? "Dados classificados" : "Classificação pendente"}</span>
        <h3>${escapeHtml(item.label)}</h3>
      </header>
      <div class="pres-department-value">
        <small>Faturamento do departamento</small>
        <strong>${escapeHtml(item.revenueLabel)}</strong>
      </div>
      <p>${escapeHtml(item.detail)}</p>
      <dl>
        <div><dt>Margem</dt><dd>Somente quando identificada</dd></div>
        <div><dt>Despesas</dt><dd>Somente do departamento</dd></div>
        <div><dt>Rentabilidade</dt><dd>Sem rateio genérico</dd></div>
      </dl>
    </article>
  `).join("");
}

function moneyOrBlocked(value, released) {
  if (!released || value == null) return "Aguardando homologação";
  return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function departmentMatrix(lines = [], released = false) {
  const labels = { combustiveis: "Combustíveis", conveniencia: "Conveniência", lubrificantes: "Lubrificantes" };
  return `<div class="pres-matrix-wrap"><table class="pres-matrix"><thead><tr><th>Empresa</th><th>Departamento</th><th>Faturamento</th><th>Margem bruta</th><th>Despesas</th><th>Resultado</th><th>Status</th></tr></thead><tbody>${lines.map((line) => `
    <tr><td><strong>${escapeHtml(line.companyName)}</strong></td><td>${labels[line.department] || escapeHtml(line.department)}</td><td>${moneyOrBlocked(line.revenue, released)}</td><td>${moneyOrBlocked(line.grossMargin, released)}</td><td>${moneyOrBlocked(line.expenses, released)}</td><td>${moneyOrBlocked(line.operatingResult, released)}</td><td><span class="pres-line-status pres-line-status--${released && line.status === "LIBERADO" ? "ok" : "blocked"}">${released && line.status === "LIBERADO" ? "Homologado" : "Bloqueado"}</span></td></tr>
  `).join("")}</tbody></table></div>`;
}

function licensedCompanies() {
  return LICENSED_COMPANIES.map((company) => `
    <span class="pres-company"><i></i>${escapeHtml(company.nome)}</span>
  `).join("");
}

export function renderPresidentDashboard(node, data, filters, options = {}) {
  if (!node) return;
  if (!data) {
    node.innerHTML = `<section class="state">Preparando o resumo da presidência...</section>`;
    return;
  }

  const availableDepartments = data.departments.filter((item) => item.status === "available").length;
  const statusTone = availableDepartments === data.departments.length ? "good" : "warn";
  const released = data.homologation?.released === true;
  const statusTitle = released ? "DRE homologada" : "DRE aguardando homologação";
  const statusText = released
    ? "Nove linhas departamentais validadas e liberadas."
    : `${data.homologation?.pendingExpenses || 0} despesa(s) ainda exigem classificação gerencial.`;
  node.innerHTML = `
    <section class="pres-page pres-page--simple">
      <header class="pres-summary">
        <div>
          <span class="pres-eyebrow">Resumo da Presidência</span>
          <h2>Como está o Grupo agora</h2>
          <p>${escapeHtml(formatPeriodBr(filters.dataInicial, filters.dataFinal))} · 3 empresas licenciadas</p>
        </div>
        <div class="pres-status pres-status--${released ? "good" : "warn"}">
          <i></i>
          <div><strong>${escapeHtml(statusTitle)}</strong><span>${escapeHtml(statusText)}</span></div>
        </div>
      </header>

      <section class="pres-license-scope" aria-label="Empresas licenciadas">
        <strong>Escopo atual</strong>
        <div>${licensedCompanies()}</div>
      </section>

      <section class="pres-department-intro">
        <div><span>Gestão WebPosto</span><h3>Resultado por departamento</h3></div>
        <p>Receitas, custos e margens não são somados entre operações.</p>
      </section>

      <section class="pres-exec-strip">
        <article><span>Empresas no escopo</span><strong>3</strong><small>Somente licenças oficiais</small></article>
        <article><span>Linhas gerenciais</span><strong>9</strong><small>3 empresas × 3 departamentos</small></article>
        <article><span>Despesas pendentes</span><strong>${data.homologation?.pendingExpenses || 0}</strong><small>Não entram na DRE</small></article>
        <article><span>Situação</span><strong>${released ? "Homologada" : "Bloqueada"}</strong><small>${released ? "Pronta para decisão" : "Sem estimativas"}</small></article>
      </section>

      <article class="pres-panel pres-matrix-panel">
        <header><div><span>Desempenho independente</span><h3>Empresa × departamento</h3></div><p>Não existe total genérico da rede.</p></header>
        ${departmentMatrix(data.departmentMatrix, released)}
      </article>

      <section class="pres-simple-grid">
        <article class="pres-panel"><header><div><span>Comparativo direto</span><h3>Desempenho das unidades</h3></div></header>${branchRows(data.branchRanking || [])}</article>
        <article class="pres-panel pres-priorities"><header><div><span>O que exige atenção</span><h3>Decisões necessárias</h3></div></header><div class="pres-decisions">${decisionItems(data)}</div></article>
      </section>

      <footer class="pres-footer">
        <span>Fonte: WebPosto · informações disponíveis no período selecionado</span>
        <div><button type="button" class="btn-secondary" id="presRefresh">Atualizar dados</button>${released ? "" : '<button type="button" class="btn-primary" id="presHomologation">Revisar pendências</button>'}</div>
      </footer>
    </section>
  `;

  node.querySelector("#presRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#presHomologation")?.addEventListener("click", () => options.onNavigate?.("financeCenter"));
}
