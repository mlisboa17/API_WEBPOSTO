import { formatCurrency, formatNumber } from "../services/format.js";
import { metricsEngine } from "../services/metricsEngine.js";

export function renderDreBlock(container, dres) {
  // Garantia DRE gerado usando Motor central
  const receitas = metricsEngine.getReceitasDRE();
  const custosProduto = metricsEngine.getCustosDRE();
  const outrasDespesas = metricsEngine.getOutrasDespesasDRE();
  const resultadoOperacional = metricsEngine.getResultadoOperacionalDRE();
  const margem = metricsEngine.getMargemDRE();

  // Validacao
  const isValidDre = parseFloat((receitas - custosProduto - outrasDespesas).toFixed(2)) === parseFloat(resultadoOperacional.toFixed(2));

  container.innerHTML = `
    <div class="panel dre-panel">
      <h3>DRE Gerencial <span style="font-size:11px;color:#888" title="Auditoria local calculo OK"> (Audit)</span></h3>
      <div class="dre-line"><span>Receitas brutas:</span> <span>${formatCurrency(receitas)}</span></div>
      <div class="dre-line negative"><span>(-) Custos Produto:</span> <span>${formatCurrency(custosProduto)}</span></div>
      <div class="dre-line negative"><span>(-) Outras Despesas:</span> <span>${formatCurrency(outrasDespesas)}</span></div>
      <hr />
      ${!isValidDre ? '<div class="alert-danger" style="margin-bottom:10px;padding:4px;font-size:12px">Divergência matemática no DRE!</div>' : ''}
      <div class="dre-line total"><span>Resultado Operacional:</span> <span class="${resultadoOperacional < 0 ? 'text-danger' : 'text-success'}">${formatCurrency(resultadoOperacional)}</span></div>
      <div class="dre-line"><span>Margem %:</span> <span>${formatNumber(margem)}% <b title="(Faturamento - Despesas) / Faturamento" style="cursor:help">ℹ️</b></span></div>
    </div>
  `;
}
