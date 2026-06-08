import { formatCurrency } from "../services/format.js";

export function renderTopNBlocks(container, topN) {
  const renderList = (items) => {
    if (!items.length) return "<div class='small text-muted'>Sem dados</div>";
    return items.map((item, idx) => `
      <div class="topn-item">
        <span class="topn-rank">${idx + 1}. ${item[0]}</span>
        <span class="topn-val">${formatCurrency(item[1])}</span>
      </div>
    `).join("");
  };

  container.innerHTML = `
    <div class="topn-grid">
      <div class="panel">
        <h3>Top 10 Despesas (Planos)</h3>
        <div class="topn-list">${renderList(topN.topDespesas)}</div>
      </div>
      <div class="panel">
        <h3>Top Formas Pagamento</h3>
        <div class="topn-list">${renderList(topN.topFormasPgto)}</div>
      </div>
    </div>
  `;
}
