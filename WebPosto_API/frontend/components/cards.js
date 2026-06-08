import { formatCurrency } from "../services/format.js";

export function renderOverviewCards(container, overview) {
  const consolidado = overview?.consolidado || {};
  container.innerHTML = `
    <div class="cards">
      <article class="card">
        <div class="label">Total despesas (rede)</div>
        <div class="value">${formatCurrency(consolidado.total_despesas)}</div>
      </article>
      <article class="card">
        <div class="label">Total contas a pagar (rede)</div>
        <div class="value">${formatCurrency(consolidado.total_a_pagar)}</div>
      </article>
      <article class="card">
        <div class="label">Postos retornados</div>
        <div class="value">${(overview?.postos || []).length}</div>
      </article>
    </div>
  `;
}
