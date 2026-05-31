export type SituacaoProduto = "todos" | "ativos" | "inativos";

export type TipoProdutoFiltro =
  | "todos"
  | "combustivel"
  | "C"
  | "P"
  | "S"
  | "U"
  | "I"
  | "O"
  | "K"
  | "8";

export interface Produto {
  id: number;
  codigo_barra?: string | null;
  codigoBarras?: string | null;
  descricao: string;
  preco_venda?: string | number;
  precoVenda?: string | number;
  preco_custo?: string | number;
  precoCusto?: string | number;
  ativo: boolean;
  ncm?: string | null;
  codigo_grupo?: number | null;
  codigoGrupo?: number | null;
  nome_grupo?: string | null;
  nomeGrupo?: string | null;
  sub_grupo_1_codigo?: number | null;
  subGrupo1Codigo?: number | null;
  sub_grupo_2_codigo?: number | null;
  subGrupo2Codigo?: number | null;
  sub_grupo_3_codigo?: number | null;
  subGrupo3Codigo?: number | null;
  tipo_produto?: string | null;
  tipoProduto?: string | null;
  tipo_combustivel?: string | null;
  tipoCombustivel?: string | null;
  combustivel?: boolean;
  cst_icms?: string | null;
  cstIcms?: string | null;
  unidade_medida?: string | null;
  unidadeMedida?: string | null;
}

export interface PaginatedProdutos {
  pagina_atual: number;
  total_paginas: number;
  total_registros: number;
  produtos: Produto[];
  fonte?: string;
  cache_hit?: boolean;
}

export interface GrupoCadastro {
  codigo: number;
  nome: string;
  tipoGrupo?: string | null;
  qtd_produtos?: number;
}

export interface SubgrupoIndice {
  codigo: number;
  nivel: 1 | 2 | 3;
  qtd: number;
}

export interface ProdutoFormPayload {
  descricao: string;
  descricaoResumida?: string;
  tipoProduto: string;
  grupoCodigo: number;
  precoVenda: number;
  precoCusto: number;
  precoCompra: number;
  unidadeCompra: string;
  unidadeVenda: string;
  codigoBarras?: string;
  codigoNcm: string;
  ativo: boolean;
  tributoIcms: {
    cstSaida: string;
    percentualIcmsSaida: number;
    cstEntrada: string;
    percentualIcmsEntrada: number;
  };
}

export interface ProdutoCrudResponse {
  ok: boolean;
  mensagem?: string;
  produto?: Produto | null;
  detail?: string;
}

export interface ProdutosQuery {
  pagina?: number;
  limite?: number;
  descricao?: string;
  grupos?: number[];
  situacao?: SituacaoProduto;
  tipoProduto?: TipoProdutoFiltro;
  subgrupos?: number[];
}
