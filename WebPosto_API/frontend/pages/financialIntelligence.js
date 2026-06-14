function scoreClass(classification) {
  const key = String(classification || "ATENÇÃO").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  return `fin-intel-score fin-intel-score--${key}`;
}

function riskBadge(level) {
  const key = String(level || "BAIXO").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  return `<span class="fin-intel-risk fin-intel-risk--${key}">${level || "—"}</span>`;
}

function trendBadge(trend) {
  const key = String(trend || "ESTABILIDADE").toLowerCase();
  return `<span class="fin-intel-trend fin-intel-trend--${key}">${trend || "—"}</span>`;
}

function formatMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function renderExecutiveSection(node, data) {
  if (!node) return;
  const score = data.executiveFinancialScore || {};
  const cards = Array.isArray(data.executiveCards) ? data.executiveCards.slice(0, 6) : [];
  node.innerHTML = `
    <div class="fin-intel-hero card">
      <div class="${scoreClass(score.classification)}">
        <span>Executive Financial Score</span>
        <strong class="fin-intel-score-value">${score.score ?? "—"}</strong>
        <em>${score.classification || "—"}</em>
      </div>
      <ul class="fin-intel-breakdown">
        <li>Liquidez ${score.components?.liquidity ?? "—"}</li>
        <li>Fluxo ${score.components?.fluxo ?? "—"}</li>
        <li>Recebíveis ${score.components?.receivables ?? "—"}</li>
        <li>Despesas ${score.components?.despesas ?? "—"}</li>
        <li>Riscos ${score.components?.risks ?? "—"}</li>
      </ul>
    </div>
    <div class="fin-ops-grid fin-ops-grid--cards">
      ${cards
        .map(
          (card) => `
        <article class="card fin-ops-card">
          <span>${card.label}</span>
          <strong>${card.value ?? "—"}</strong>
          <small>${card.detail || "—"}</small>
        </article>`
        )
        .join("")}
    </div>
  `;
}

function renderTrendsSection(node, trends) {
  if (!node) return;
  const horizon = trends?.horizons?.["7d"] || {};
  const dims = ["receitas", "despesas", "fluxo", "recebimentos", "pagamentos"];
  node.innerHTML = `
    <p class="muted">Tendência geral: ${trendBadge(trends?.overallTrend)} · ${trends?.snapshotsAvailable ?? 0} snapshots</p>
    <div class="fin-ops-grid">
      ${dims
        .map((dim) => {
          const row = horizon[dim] || {};
          return `
          <article class="card fin-ops-card">
            <span>${dim}</span>
            <strong>${trendBadge(row.classification)}</strong>
            <small>${row.deltaPct != null ? `${row.deltaPct.toFixed(1)}%` : "sem baseline"}</small>
          </article>`;
        })
        .join("")}
    </div>
  `;
}

function renderRisksSection(node, risks) {
  if (!node) return;
  const rows = Array.isArray(risks?.risks) ? risks.risks : [];
  node.innerHTML = `
    <p class="muted">Nível geral: ${riskBadge(risks?.overallLevel)}</p>
    <ul class="fin-ops-alert-list">
      ${rows
        .map(
          (row) =>
            `<li>${riskBadge(row.level)} <strong>${row.title}</strong> <span class="muted">(${row.code})</span></li>`
        )
        .join("")}
    </ul>
  `;
}

function renderOpportunitiesSection(node, opportunities) {
  if (!node) return;
  const rows = Array.isArray(opportunities?.opportunities) ? opportunities.opportunities : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Nenhuma oportunidade identificada no snapshot.</p>`;
    return;
  }
  node.innerHTML = `
    <ul class="fin-ops-alert-list">
      ${rows
        .slice(0, 6)
        .map(
          (row) =>
            `<li><strong>${row.title}</strong> · impacto ${formatMoney(row.impacto_estimado)} · origem ${row.origem}</li>`
        )
        .join("")}
    </ul>
  `;
}

function renderCashFlowSection(node, cashFlow) {
  if (!node) return;
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card">
        <span>Saúde do fluxo</span>
        <strong>${cashFlow?.cashFlowHealth || "—"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Fluxo atual</span>
        <strong>${formatMoney(cashFlow?.currentFluxo)}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Deteriorando?</span>
        <strong>${cashFlow?.fluxoDeteriorando ? "Sim" : "Não"}</strong>
      </article>
    </div>
    ${
      cashFlow?.strongestPeriod
        ? `<p class="muted">Período mais forte: ${cashFlow.strongestPeriod.period?.dataInicial} → ${cashFlow.strongestPeriod.period?.dataFinal}</p>`
        : ""
    }
    ${
      cashFlow?.weakestPeriod
        ? `<p class="muted">Período mais fraco: ${cashFlow.weakestPeriod.period?.dataInicial} → ${cashFlow.weakestPeriod.period?.dataFinal}</p>`
        : ""
    }
  `;
}

function renderCommitmentsSection(node, commitments) {
  if (!node) return;
  const rec = commitments?.receivables || {};
  const pay = commitments?.payables || {};
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card">
        <span>Recebíveis</span>
        <strong>${rec.health || "—"}</strong>
        <small>${formatMoney(rec.total)} · ${rec.rows ?? 0} títulos</small>
      </article>
      <article class="card fin-ops-card">
        <span>Pagáveis</span>
        <strong>${pay.health || "—"}</strong>
        <small>${formatMoney(pay.total)} · ${pay.rows ?? 0} títulos</small>
      </article>
      <article class="card fin-ops-card">
        <span>Inadimplência</span>
        <strong>${commitments?.delinquencyRelevant ? "Relevante" : "Baixa"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Concentração</span>
        <strong>${commitments?.concentrationRelevant ? "Sim" : "Não"}</strong>
      </article>
    </div>
  `;
}

export function renderFinancialIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  const data = payload?.data || payload || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Financial Intelligence Center</h2>
        <p class="muted">F08.4 — tendências, riscos e oportunidades com evidência auditável (snapshot-first).</p>
      </div>
      <div class="fin-ops-actions">
        <button type="button" class="btn-secondary" id="finIntelRefresh">Atualizar</button>
      </div>
    </header>
    <p class="fin-monitor-meta muted">
      Período: ${filters?.dataInicial || data.period?.dataInicial || "—"} →
      ${filters?.dataFinal || data.period?.dataFinal || "—"}
      · Sem IA generativa · Sem forecast inventado
      · Gerado em ${(data.generatedAt || "").replace("T", " ")}
    </p>

    <section class="fin-intel-section"><h3>Visão Executiva</h3><div id="finIntelExecutive"></div></section>
    <section class="fin-intel-section card"><h3>Tendências</h3><div id="finIntelTrends"></div></section>
    <section class="fin-intel-section card"><h3>Riscos</h3><div id="finIntelRisks"></div></section>
    <section class="fin-intel-section card"><h3>Oportunidades</h3><div id="finIntelOpportunities"></div></section>
    <section class="fin-intel-section card"><h3>Fluxo Financeiro</h3><div id="finIntelCashFlow"></div></section>
    <section class="fin-intel-section card"><h3>Recebíveis / Pagáveis</h3><div id="finIntelCommitments"></div></section>
  `;

  renderExecutiveSection(node.querySelector("#finIntelExecutive"), data);
  renderTrendsSection(node.querySelector("#finIntelTrends"), data.trends);
  renderRisksSection(node.querySelector("#finIntelRisks"), data.risks);
  renderOpportunitiesSection(node.querySelector("#finIntelOpportunities"), data.opportunities);
  renderCashFlowSection(node.querySelector("#finIntelCashFlow"), data.cashFlow);
  renderCommitmentsSection(node.querySelector("#finIntelCommitments"), data.commitments);

  node.querySelector("#finIntelRefresh")?.addEventListener("click", () => options.onRefresh?.());
}
