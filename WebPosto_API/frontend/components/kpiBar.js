import { formatCurrency, formatNumber } from "../services/format.js";
import { metricsEngine } from "../services/metricsEngine.js";

function getExpl($label) {
  const map = {
    'Faturamento Total': 'VENDA + DESPESAS\\nSoma de todos os recebimentos.',
    'Despesas Totais': 'CONSULTAR_DESPESAS_FINANCEIRO_REDE\\nGastos pagos e não pagos no prazo.',
    'Resultado': 'Faturamento - Custos - Outras Despesas.',
    'Ticket Médio': 'Faturamento / Vendas (Quantidade unificada).',
    'Qtd Vendas': 'Endpoint: VENDA',
    'Clientes': 'Endpoint: VENDA (Contagem por Nomes únicos)',
    'Estoque Total': 'Endpoint: PRODUTO_ESTOQUE'
  };
  return map[$label] || '';
}

export function renderKpiBar(container, metricsObj, stockObj) {
  // O template reaproveita o motor central "metricsEngine" para o valor auditavel.
  container.innerHTML = `
    <div class="kpi-bar">
      <div class="kpi-item">
        <span class="kpi-label">Faturamento Total <b title="${getExpl('Faturamento Total')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val">${formatCurrency(metricsEngine.getFaturamento())}</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Despesas Totais <b title="${getExpl('Despesas Totais')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val">${formatCurrency(metricsEngine.getDespesasTotais())}</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Resultado <b title="${getExpl('Resultado')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val ${metricsEngine.getResultado() < 0 ? 'text-danger' : 'text-success'}">${formatCurrency(metricsEngine.getResultado())}</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Ticket Médio <b title="${getExpl('Ticket Médio')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val">${formatCurrency(metricsEngine.getTicketMedio())}</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Qtd Vendas <b title="${getExpl('Qtd Vendas')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val">${formatNumber(metricsEngine.getQtdVendas())}</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Clientes <b title="${getExpl('Clientes')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val">${formatNumber(metricsEngine.getQtdClientes())}</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Estoque Total <b title="${getExpl('Estoque Total')}" style="cursor:help">ℹ️</b></span>
        <span class="kpi-val">${formatNumber(metricsEngine.getEstoqueTotal())}</span>
      </div>
    </div>
  `;
}
