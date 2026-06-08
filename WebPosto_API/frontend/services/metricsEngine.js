import { computeIndicators, computeDRE, computeStockIndicator } from "./analyticsEngine.js";

/**
 * Motor Central de Metricas.
 * Ele expoe funcoes restritas de chamadas e impede o recalculo nas telas.
 * Depende e envolve o \`analyticsEngine\` validando os inputs.
 */
class MetricsEngine {
  constructor() {
    this.sales = [];
    this.expenses = [];
    this.stock = [];
    
    // Lazy loaded / Memoized values
    this._inds = null;
    this._dre = null;
    this._stk = null;
  }

  mount(sales = [], expenses = [], stock = []) {
    this.sales = sales;
    this.expenses = expenses;
    this.stock = stock;
    
    this._inds = computeIndicators(this.sales, this.expenses);
    this._dre = computeDRE(this.sales, this.expenses);
    this._stk = computeStockIndicator(this.stock);
  }

  getFaturamento() {
    return this._inds?.faturamento || 0;
  }

  getDespesasTotais() {
    return this._inds?.despesasTotais || 0;
  }

  getResultado() {
    return this._inds?.resultado || 0;
  }

  getTicketMedio() {
    return this._inds?.ticketMedio || 0;
  }
  
  getQtdVendas() {
    return this._inds?.qtdVendas || 0;
  }

  getQtdClientes() {
    return this._inds?.qtdClientes || 0;
  }

  getEstoqueTotal() {
    return this._stk?.estoqueTotal || 0;
  }

  getReceitasDRE() {
    return this._dre?.receitas || 0;
  }

  getCustosDRE() {
    return this._dre?.custosProduto || 0;
  }

  getOutrasDespesasDRE() {
    return this._dre?.outrasDespesas || 0;
  }

  getResultadoOperacionalDRE() {
    return this._dre?.resultadoOperacional || 0;
  }

  getMargemDRE() {
    return this._dre?.margem || 0;
  }
}

export const metricsEngine = new MetricsEngine();
