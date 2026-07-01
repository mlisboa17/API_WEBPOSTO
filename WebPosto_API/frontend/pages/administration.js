import {
  renderExecutiveFirstFold,
  wrapExecutiveDetail,
  bindExecutiveNav,
} from "../components/executiveFirstFold.js";
import { buildFourQuestionBrief } from "../services/executiveBrief.js";
import { periodSubtitle } from "../services/executiveKpis.js";

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
    body: "Integração WebPosto e proteção automática de falhas.",
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
      <h3>Proteção de integração</h3>
      <div class="circuit-summary">
        <article><span>Financeiro aberto</span><strong>${financial.OPEN ?? 0}</strong></article>
        <article><span>Em recuperação</span><strong>${financial.HALF_OPEN ?? 0}</strong></article>
        <article><span>Operacional</span><strong>${financial.CLOSED ?? 0}</strong></article>
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
    panel.innerHTML = `<p class="muted">Falha ao carregar status de integração: ${error.message}</p>`;
  }
}

function buildAdminDetail(section, meta) {
  const circuitBlock =
    section === "integracoes"
      ? `<article class="card admin-card"><div id="circuitPanel">Carregando status de integração…</div></article>`
      : "";
  return `
    <section class="admin-panel card">
      <div class="admin-grid">
        <article class="card admin-card">
          <h3>${meta.title}</h3>
          <p>${meta.body}</p>
        </article>
        ${circuitBlock}
        <article class="card admin-card">
          <h3>Referência técnica</h3>
          <ul class="admin-list">
            <li>Módulo de resiliência financeira</li>
            <li>Serviço de dados consolidados</li>
            <li>Armazenamento de histórico financeiro</li>
          </ul>
        </article>
      </div>
    </section>`;
}

export function renderAdministration(node, _payload, filters, options = {}) {
  if (!node) return;
  const section = options.section || "filiais";
  const meta = ADMIN_SECTIONS[section] || ADMIN_SECTIONS.filiais;

  const brief = buildFourQuestionBrief({
    what: `Administração — ${meta.title}.`,
    why: "Configuração e governança do ecossistema LOGOS SPACE.",
    where: section === "integracoes" ? "Integrações WebPosto" : meta.title,
    actionNow:
      section === "integracoes"
        ? "Verificar proteção de integração e circuit breakers."
        : `Revisar configuração de ${meta.title.toLowerCase()}.`,
  });

  const firstFold = renderExecutiveFirstFold({
    title: "Administração",
    subtitle: periodSubtitle(filters),
    actionsHtml: "",
    kpis: [
      { label: "Módulo", value: meta.title.slice(0, 12), trendPct: null, status: "ok" },
      { label: "Escopo", value: section, trendPct: null, status: "ok" },
      { label: "API", value: "Local", trendPct: null, status: "ok" },
      { label: "Alertas", value: section === "integracoes" ? "Monitor" : "—", trendPct: null, status: "ok" },
    ],
    brief,
    chartBars: [],
    chartTitle: "Governança",
    criticalBranches: [],
    priorityActions: [],
    risks: [],
    opportunities: [],
    alerts: [],
  });

  node.innerHTML = `${firstFold}${wrapExecutiveDetail(buildAdminDetail(section, meta), "Configuração e referências")}`;
  bindExecutiveNav(node, options.onNavigate);

  if (section === "integracoes") {
    mountCircuitPanel(node);
  }
}
