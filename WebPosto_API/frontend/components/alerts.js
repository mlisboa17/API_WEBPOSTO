export function renderAlerts(container, alerts) {
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <div class="panel alerts-panel empty">
        <span class="icon">✅</span> Tudo em ordem! Nenhum alerta gerencial.
      </div>
    `;
    return;
  }

  const items = alerts.map(a => `
    <div class="alert-item alert-${a.tipo}">
      <span class="icon">${a.tipo === "danger" ? "🚨" : "⚠️"}</span>
      ${a.mensagem}
    </div>
  `).join("");

  container.innerHTML = `
    <div class="panel alerts-panel">
      <h3>Alertas Gerenciais (${alerts.length})</h3>
      <div class="alerts-list">
        ${items}
      </div>
    </div>
  `;
}