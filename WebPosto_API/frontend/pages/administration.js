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
    body: "Gateway WebPosto unificado (Onda 2) — tokens, retries, snapshot-first.",
  },
  configuracoes: {
    title: "Configurações",
    body: "Parâmetros do ecossistema LOGOS SPACE e cockpit financeiro.",
  },
};

export function renderAdministration(node, _payload, _filters, options = {}) {
  if (!node) return;
  const section = options.section || "filiais";
  const meta = ADMIN_SECTIONS[section] || ADMIN_SECTIONS.filiais;
  node.innerHTML = `
    <section class="admin-panel card">
      <header class="section-header">
        <h2>⚙️ Administração — ${meta.title}</h2>
        <p>Configuração do ecossistema (UX-01 — sem alteração de motores/APIs).</p>
      </header>
      <div class="admin-grid">
        <article class="card admin-card">
          <h3>${meta.title}</h3>
          <p>${meta.body}</p>
        </article>
        <article class="card admin-card">
          <h3>Artefatos</h3>
          <ul class="admin-list">
            <li>app_core/filial_registry.py</li>
            <li>gateway/webposto_client.py</li>
            <li>frontend/data/filiais.json</li>
          </ul>
        </article>
      </div>
    </section>
  `;
}
