export type Periodo = "hoje" | "7d" | "mensal";

export interface UnidadeWebPosto {
  fantasia?: string;
  razao_social?: string;
  cnpj?: string;
  base_url?: string;
  chave_mascarada?: string;
  empresa_codigo?: number;
}

export interface CombustivelMetrica {
  nome?: string;
  codigo?: string;
  litros?: number;
  valor?: number;
  quantidade?: number;
}

export interface AdelaideMetrics {
  faturamento_bruto: number;
  faturamento_nao_combustivel: number;
  galonagem_total: number;
  credito_recuperavel: number;
  despesas_caixa: number;
  margem_liquida_real: number;
  periodo: string;
  status_api: string;
  fallback: boolean;
  dados_reais: boolean;
  mensagem?: string | null;
  unidade?: UnidadeWebPosto | null;
  combustiveis: CombustivelMetrica[];
  por_produto: Record<string, unknown>[];
  qtd_abastecimentos: number;
  qtd_itens_venda: number;
  data_inicial?: string | null;
  data_final?: string | null;
}
