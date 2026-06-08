/**
 * @typedef {Object} VendaItem
 * @property {number} empresaCodigo - Código da empresa.
 * @property {number} vendaCodigo - Identificador da venda pai.
 * @property {number} vendaItemCodigo - Identificador único do item da venda.
 * @property {string} dataMovimento - Data em ISO.
 * @property {number|string} produtoCodigo - Código do produto vendido.
 * @property {number|string} quantidade - Quantidade comercializada.
 * @property {number|string} precoCusto - Valor unitário de custo.
 * @property {number|string} totalCusto - Valor total (custo).
 * @property {number|string} precoVenda - Valor unitário de venda.
 * @property {number|string} totalVenda - Valor total (venda).
 * @property {number|string} [codigo] - Código auxiliar (se aplicável).
 */

/**
 * @typedef {Object} VendaFormaPagamento
 * @property {number} empresaCodigo - Código da empresa.
 * @property {number} vendaCodigo - Identificador da venda.
 * @property {number} vendaPrazoCodigo - Identificador da parcela (se aplicável).
 * @property {string} dataMovimento - Data em ISO.
 * @property {number|string} valorPagamento - Valor pago nesta modalidade.
 * @property {number|string} formaPagamentoCodigo - Identificador da forma de pgto.
 * @property {string} nomeFormaPagamento - Ex: DINHEIRO, PIX, C.CREDITO.
 * @property {number|string} [codigo] - Código auxiliar.
 */

/**
 * @typedef {Object} Venda
 * @property {number} empresaCodigo
 * @property {number} vendaCodigo
 * @property {string} data
 * @property {number|string} total_venda
 * @property {string} [cliente]
 * @property {VendaItem[]} itens
 * @property {VendaFormaPagamento[]} pagamentos
 */

export {};