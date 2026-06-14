const ADMIN_SECTIONS = {
  filiais: {
    title: "Filiais",
    body: "Registry Onda 1 — app_core/filial_registry.py e manifest frontend/data/filiais.json.",
  },
  usuarios: {
    title: "Usuários",
    body: "Gestão de usuários corporativos (configuração local — sem alteração de API nesta onda).",
  },
  permissoes: {
    title: "Permissões",
    body: "Políticas de acesso por perfil e filial (empresaCodigo como chave lógica).",
  },
  integracoes: {
    title: "Integrações",
    body: "Gateway WebPosto + resiliência F08.0 — circuit breaker e snapshot financeiro.",
  },
  configuracoes: {
    title: "Configurações",
    body: "Parâmetros do ecossistema LOGOS SPACE e cockpit financeiro.",
  },
};

function renderCircuitBadge(status) {
  const cls = String(status || "CLOSED").toLowerCase().replace("_", "-");
  return `<span class="circuit-badge circuit-badge--${cls}">${status}</span>`;
}

async function mountCircuitPanel(node) {
  const panel = node.querySelector("#circuitPanel");
  if (!panel) return;
  try {
    const { fetchCircuitBreakerStatus, resetCircuitBreaker } = await import("../services/api.js");
    const resp = await fetchCircuitBreakerStatus();
    const data = resp?.data || {};
    const summary = data.summary || {};
    const endpoints = data.endpoints || {};
    const financial = summary.financial || {};
    panel.innerHTML = `
      <h3>Circuit Status (F08.0)</h3>
      <div class="circuit-summary">
        <article><span>Financeiro OPEN</span><strong>${financial.OPEN ?? 0}</strong></article>
        <article><span>HALF_OPEN</span><strong>${financial.HALF_OPEN ?? 0}</strong></article>
        <article><span>CLOSED</span><strong>${financial.CLOSED ?? 0}</strong></article>
      </div>
      <div class="circuit-actions">
        <button type="button" data-reset="financial" class="btn-secondary">Reset financeiro</button>
        <button type="button" data-reset="fuel" class="btn-secondary">Reset combustível</button>
        <button type="button" data-reset="fiscal" class="btn-secondary">Reset fiscal</button>
        <button type="button" data-reset="global" class="btn-secondary">Reset global</button>
      </div>
      <details class="circuit-details">
        <summary>Endpoints (${Object.keys(endpoints).length})</summary>
        <ul class="admin-list">
          ${Object.entries(endpoints)
            .slice(0, 24)
            .map(([key, status]) => `<li>${key} ${renderCircuitBadge(status)}</li>`)
            .join("")}
        </ul>
      </details>
    `;
    panel.querySelectorAll("[data-reset]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const scope = btn.getAttribute("data-reset");
        await resetCircuitBreaker(scope);
        await mountCircuitPanel(node);
      });
    });
  } catch (error) {
    panel.innerHTML = `<p class="muted">Falha ao carregar circuit status: ${error.message}</p>`;
  }
}

export function renderAdministration(node, _payload, _filters, options = {}) {
  if (!node) return;
  const section = options.section || "filiais";
  const meta = ADMIN_SECTIONS[section] || ADMIN_SECTIONS.filiais;
  const circuitBlock =
    section === "integracoes"
      ? `<article class="card admin-card"><div id="circuitPanel">Carregando circuit status…</div></article>`
      : "";
  node.innerHTML = `
    <section class="admin-panel card">
      <header class="section-header">
        <h2>⚙️ Administração — ${meta.title}</h2>
        <p>Configuração do ecossistema (F08.0 resiliência financeira).</p>
      </header>
      <div class="admin-grid">
        <article class="card admin-card">
          <h3>${meta.title}</h3>
          <p>${meta.body}</p>
        </article>
        ${circuitBlock}
        <article class="card admin-card">
          <h3>Artefatos</h3>
          <ul class="admin-list">
            <li>src/services/financial_resilience_service.py</li>
            <li>src/services/financial_snapshot_service.py</li>
            <li>snapshots/financial/</li>
          </ul>
        </article>
      </div>
    </section>
  `;
  if (section === "integracoes") {
    mountCircuitPanel(node);
  }
}
