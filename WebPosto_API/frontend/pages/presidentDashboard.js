import { LICENSED_COMPANIES } from "../config/managementScope.js";
import { formatPeriodBr } from "../services/format.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function money(value) {
  return Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function branchRows(rows = []) {
  if (!rows.length) {
    return `<p class="pres-empty">Ainda não há dados confiáveis por unidade neste período.</p>`;
  }
  const visible = rows.slice(0, 3);
  const max = Math.max(...visible.map((row) => Number(row.value || 0)), 1);
  return visible.map((row, index) => `
    <div class="pres-branch-row">
      <span class="pres-branch-position">${index + 1}</span>
      <div class="pres-branch-main">
        <strong>${escapeHtml(row.label)}</strong>
        <div class="pres-branch-track"><i style="width:${Math.max(4, (Number(row.value || 0) / max) * 100)}%"></i></div>
      </div>
      <strong class="pres-branch-value">${row.available === false || row.value == null ? "Dados indisponíveis" : money(row.value)}</strong>
    </div>
  `).join("");
}

function decisionItems(data, released) {
  const alerts = data.alerts || [];
  if (alerts.length) {
    return alerts.slice(0, 3).map((item, index) => `
      <div class="pres-decision pres-decision--${item.tone}">
        <b>${index + 1}</b>
        <div>
          <span>${item.tone === "bad" ? "Ação imediata" : "Acompanhar"}</span>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.detail)}</p>
        </div>
      </div>
    `).join("");
  }
  if (!released) {
    return `
      <div class="pres-decision pres-decision--warn">
        <b>1</b>
        <div>
          <span>Antes de decidir</span>
          <strong>Concluir a homologação da DRE</strong>
          <p>Receitas podem ser acompanhadas, mas lucro e rentabilidade continuam bloqueados até a validação financeira.</p>
        </div>
      </div>
    `;
  }
  const insight = data.insights?.[0];
  return `
    <div class="pres-decision pres-decision--good">
      <b>✓</b>
      <div>
        <span>Leitura do período</span>
        <strong>Nenhuma ocorrência crítica calculada</strong>
        <p>${escapeHtml(insight?.text || "Confira a cobertura dos dados antes de concluir o fechamento.")}</p>
      </div>
    </div>
  `;
}

function ownerKpis(data, released) {
  const [revenue, margin] = data.kpis || [];
  const pending = Number(data.homologation?.pendingExpenses || 0);
  return `
    <article class="pres-owner-kpi pres-owner-kpi--primary">
      <span>Receita observada</span>
      <strong>${escapeHtml(revenue?.value || "Dados indisponíveis")}</strong>
      <small>${escapeHtml(revenue?.delta || "Período selecionado")} · ainda não representa lucro</small>
    </article>
    <article class="pres-owner-kpi pres-owner-kpi--${released ? "good" : "locked"}">
      <span>Resultado do grupo</span>
      <strong>${released ? escapeHtml(margin?.value || "Dados indisponíveis") : "Em validação"}</strong>
      <small>${released ? escapeHtml(margin?.delta || "DRE homologada") : "Aguardando homologação financeira"}</small>
    </article>
    <article class="pres-owner-kpi pres-owner-kpi--${pending ? "warn" : "good"}">
      <span>Pendências financeiras</span>
      <strong>${pending}</strong>
      <small>${pending ? "Exigem classificação gerencial" : "Nenhuma despesa pendente"}</small>
    </article>
  `;
}

function departmentSummary(departments = []) {
  return departments.map((item) => `
    <article class="pres-owner-dept pres-owner-dept--${item.status}">
      <div>
        <span>${escapeHtml(item.label)}</span>
        <small>${item.status === "available" ? "Receita identificada" : "Cobertura pendente"}</small>
      </div>
      <strong>${escapeHtml(item.revenueLabel)}</strong>
    </article>
  `).join("");
}

function moneyOrBlocked(value, released) {
  if (!released || value == null) return "Aguardando homologação";
  return money(value);
}

function departmentMatrix(lines = [], released = false) {
  const labels = {
    combustiveis: "Combustíveis",
    conveniencia: "Conveniência",
    lubrificantes: "Lubrificantes",
  };
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
    node.innerHTML = `<section class="state">Preparando a visão do proprietário...</section>`;
    return;
  }

  const released = data.homologation?.released === true;
  const alertCount = (data.alerts || []).length;
  const leader = (data.branchRanking || []).find((item) => item.available !== false);
  const statusTitle = released
    ? "Números liberados para decisão"
    : "Fechamento ainda não homologado";
  const statusText = released
    ? "Resultado e rentabilidade validados pela governança financeira."
    : "Acompanhe receitas e exceções; não use os dados atuais como lucro.";

  node.innerHTML = `
    <section class="pres-page pres-owner-page">
      <header class="pres-owner-hero">
        <div class="pres-owner-heading">
          <span class="pres-eyebrow">Visão do proprietário</span>
          <h2>O que precisa da sua atenção</h2>
          <p>${escapeHtml(formatPeriodBr(filters.dataInicial, filters.dataFinal))} · Grupo LOGOS SPACE</p>
        </div>
        <div class="pres-owner-status pres-owner-status--${released ? "good" : "warn"}">
          <i></i>
          <div><strong>${escapeHtml(statusTitle)}</strong><span>${escapeHtml(statusText)}</span></div>
        </div>
      </header>

      <section class="pres-owner-kpis" aria-label="Indicadores principais">
        ${ownerKpis(data, released)}
      </section>

      <section class="pres-owner-focus">
        <article class="pres-owner-card pres-owner-actions">
          <header>
            <div>
              <span>Prioridade de hoje</span>
              <h3>${alertCount ? `${alertCount} ponto(s) para acompanhar` : "Uma decisão antes do fechamento"}</h3>
            </div>
            ${released ? '<em class="pres-owner-badge pres-owner-badge--good">Homologado</em>' : '<em class="pres-owner-badge">Revisão necessária</em>'}
          </header>
          <div class="pres-decisions">${decisionItems(data, released)}</div>
          ${released ? "" : '<button type="button" class="btn-primary pres-owner-cta" id="presHomologation">Abrir pendências financeiras</button>'}
        </article>

        <article class="pres-owner-card pres-owner-ranking">
          <header><div><span>Unidades</span><h3>Quem está puxando o resultado</h3></div></header>
          ${branchRows(data.branchRanking || [])}
          <p class="pres-owner-context">${leader ? `${escapeHtml(leader.label)} lidera a receita observada no período.` : "Ranking indisponível para este recorte."}</p>
        </article>
      </section>

      <section class="pres-owner-section">
        <header>
          <div><span>Operações separadas</span><h3>Receita por departamento</h3></div>
          <p>Sem misturar combustíveis, conveniência e lubrificantes.</p>
        </header>
        <div class="pres-owner-departments">${departmentSummary(data.departments)}</div>
      </section>

      <details class="pres-owner-details">
        <summary><span>Ver memória de cálculo</span><small>Empresa × departamento, status e evidências</small></summary>
        <div class="pres-owner-details-body">${departmentMatrix(data.departmentMatrix, released)}</div>
      </details>

      <footer class="pres-footer">
        <span>Fonte: WebPosto · informações disponíveis no período selecionado</span>
        <div><button type="button" class="btn-secondary" id="presRefresh">Atualizar dados</button></div>
      </footer>
    </section>
  `;

  node.querySelector("#presRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#presHomologation")?.addEventListener("click", () => options.onNavigate?.("financeCenter"));
}
