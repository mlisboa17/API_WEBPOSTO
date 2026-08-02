/**
 * Tipagem de dados para o Cockpit Executivo — Sprint 51.
 * Espelha fielmente os DTOs do backend FastAPI.
 */

export interface ExecutiveSynthesis {
  period_start: string;
  period_end: string;
  generated_at: string;
  total_revenue: number | null;
  total_gross_margin: number | null;
  gross_margin_pct: number | null;
  fuel_revenue: number | null;
  fuel_margin_per_liter: number | null;
  fuel_liters_sold: number | null;
  convenience_revenue: number | null;
  pending_expenses_count: number;
  pending_expenses_value: number;
  critical_alerts: Record<string, unknown>[];
  companies_analyzed: number;
}

export interface CashCycleAnalysis {
  period_start: string;
  period_end: string;
  vacuo_financeiro_dias: number;
  necessidade_capital_giro_rs: number;
  status: 'NORMAL' | 'WARNING' | 'CRITICO';
}

export interface ExecutiveAlert {
  id: number;
  alert_external_id: string;
  category: 'QUEBRA_CAIXA' | 'DESVIO_TANQUE' | 'ESTOURO_VACUO' | 'RUPTURA_CURVA_A';
  severity: 'CRITICAL' | 'WARNING';
  title: string;
  description: string;
  impact_rs: number | null;
  unit_id: number | null;
  data_referencia: string;
  is_resolved: boolean;
  created_at: string;
}

export interface DashboardBundle {
  period: {
    start: string;
    end: string;
  };
  synthesis: ExecutiveSynthesis;
  cash_cycle: CashCycleAnalysis;
  active_alerts: ExecutiveAlert[];
  top_risks: Array<{
    title: string;
    impact_rs: number;
    severity: 'CRITICAL' | 'WARNING';
  }>;
  top_opportunities: Array<{
    title: string;
    potential_rs: number;
    type: string;
  }>;
}

export interface DreLine {
  companyName: string;
  department: 'combustiveis' | 'conveniencia' | 'lubrificantes' | 'outros';
  revenue: number;
  cost: number;
  grossMargin: number;
  expenses: number;
  operatingResult: number;
  operatingMarginPct: number;
  status: 'ESTAVEL' | 'ALERTA' | 'CRITICO';
}

export interface ReviewableFact {
  factId: string;
  companyCode: string;
  companyName: string;
  date: string;
  amount: number;
  description: string;
  supplier: string;
  managementCategory: string;
  managementAccountCode: string | null;
}

export interface FinancialAging {
  vencido: { count: number; valor: number };
  emAberto: { count: number; valor: number };
  aVencer: { count: number; valor: number };
  pago?: { count: number; valor: number };
  recebido?: { count: number; valor: number };
}

export interface SimulationInput {
  delta_preco_bomba_rs: number;
  variacao_volume_pct: number;
  taxa_antecipacao_mensal_pct?: number;
}

export interface SimulationResult {
  faturamento_projetado_rs: number;
  impacto_faturamento_rs: number;
  ebitda_projetado_rs: number;
  impacto_ebitda_rs: number;
  margem_liquida_pos_cartoes_projetada_rs: number;
  variacao_margem_liquida_rs: number;
  necessidade_capital_projetada_rs: number;
  impacto_capital_giro_rs: number;
}

export interface FuelProduct {
  produto: string;
  empresa_codigo: number;
  nome_filial: string;
  litros: string;
  valor: string;
  transacoes: number;
  percentual_rede: string;
}

export interface FuelSummary {
  total_litros: string;
  total_valor: string;
  total_transacoes: number;
  por_filial: FuelProduct[];
  por_produto: FuelProduct[];
  observacao: string;
}

export interface ConvenienceFilial {
  empresa_codigo: number;
  nome: string;
  receita: string;
  itens: number;
  unidades: string;
  departamentos: Array<{ departamento: string; valor: string; quantidade: string }>;
}

export interface CashReconciliationNature {
  natureza: string;
  label: string;
  valor_apurado: string;
  valor_apresentado: string;
  diferenca: string;
  status: string;
}

export interface ReconciliationSummary {
  valor_apurado: string;
  valor_apresentado: string;
  valor_conferido: string;
  valor_divergente: string;
  valor_pendente: string;
  naturezas: CashReconciliationNature[];
}

export interface CashHoleDetail {
  funcionario_codigo: number;
  funcionario_nome: string;
  turno: string;
  valor_dinheiro: string;
  valor_cheque: string;
  valor_pix: string;
  valor_cartao: string;
  transacoes: number;
}

export interface ExpenseCategory {
  categoria: string;
  valor: string;
}

export interface ExpenseByCompany {
  empresa_codigo: number;
  nome: string;
  valor: string;
}

export interface AutoClassifiedExpense {
  fact_id: string;
  company_code: number;
  company_name: string;
  date: string;
  amount: string;
  category: string;
  original_taxonomy: string | null;
  text: string;
}

export interface Block1Combustiveis {
  titulo: string;
  status: string;
  periodo: { inicio: string; fim: string };
  resumo: FuelSummary;
  ranking_filial: FuelProduct[];
}

export interface Block3Margens {
  titulo: string;
  status: string;
  periodo: { inicio: string; fim: string };
  faturamento_por_litro: Array<{
    empresa_codigo: number;
    nome: string;
    litros: string;
    valor: string;
    receita_por_litro: string;
  }>;
  observacao: string;
}

export interface Block4Conveniencia {
  titulo: string;
  status: string;
  periodo: { inicio: string; fim: string };
  receita_total: string;
  ticket_medio: string;
  quantidade_itens: number;
  quantidade_unidades: string;
  produtos_distintos: number;
  filiais: ConvenienceFilial[];
  top_departamentos: Array<{ departamento: string; valor: string; quantidade: string }>;
  top_produtos: Array<{ produto: string; quantidade: string; valor: string }>;
  observacao: string;
}

export interface Block5Dre {
  titulo: string;
  status: string;
  periodo: { inicio: string; fim: string };
  departamentos_confirmados: Array<{
    empresa_codigo: number;
    nome: string;
    departamento: string;
    confirmed_dre_amount: string;
    confirmed_matches: number;
    unmatched: number;
  }>;
  despesas_auto_classificadas: AutoClassifiedExpense[];
  resumo_auto_classificacao: {
    total_classificadas: number;
    remanescentes_nao_classificadas: number;
    valor_por_categoria: Record<string, string>;
  };
}

export interface Block6Despesas {
  titulo: string;
  status: string;
  periodo: { inicio: string; fim: string };
  total_despesas_gerenciais: string;
  por_categoria: ExpenseCategory[];
  por_empresa: ExpenseByCompany[];
  auto_classificadas: AutoClassifiedExpense[];
}

export interface AbastecimentoPendente {
  id: number;
  data: string;
  hora: string;
  bico: number;
  produto: string;
  litros: number;
  valor: number;
  empresa_nome: string;
  frentista_nome: string | null;
  turno: string | null;
  minutos_pendente: number;
  alerta_tipo: string;
}

export interface ResumoPendentesFilial {
  empresa_codigo: number;
  empresa_nome: string;
  total_pendentes: number;
  litros_pendentes: number;
  valor_pendente: number;
}

export interface AuditoriaPista {
  total_abastecimentos: number;
  total_pendentes: number;
  litros_pendentes: string;
  valor_pendente: string;
  alertas_retencao: number;
  alertas_divergencia_tef: number;
  por_filial: ResumoPendentesFilial[];
  por_frentista: Array<{
    frentista: string;
    total_pendentes: number;
    litros: number;
    valor: number;
    alertas: number;
  }>;
  por_bico: Array<{
    bico: number;
    filial: string;
    total_pendentes: number;
    litros: number;
    valor: number;
  }>;
  por_turno: Array<{
    turno: string;
    total_pendentes: number;
    litros: number;
    valor: number;
    alertas: number;
  }>;
  pendentes_detalhados: AbastecimentoPendente[];
}

export interface Block9Anomalias {
  titulo: string;
  status: string;
  divergencias_caixa: ReconciliationSummary;
  detalhamento_pagamento: Array<{ natureza: string; valor: string; transacoes: number }>;
  rombo_por_operador_turno: CashHoleDetail[];
  alertas: Array<Record<string, unknown>>;
  auditoria_pista: AuditoriaPista | null;
}

export interface ExecutiveReport {
  gerado_em: string;
  sprint: string;
  periodo_principal: { inicio: string; fim: string };
  filiais_monitoradas: Array<{ empresa_codigo: number; nome: string }>;
  bloco_1_combustiveis: Block1Combustiveis;
  bloco_3_margens: Block3Margens;
  bloco_4_conveniencia: Block4Conveniencia;
  bloco_5_dre: Block5Dre;
  bloco_6_despesas: Block6Despesas;
  bloco_9_anomalias: Block9Anomalias;
}

export interface TankPrediction {
  produto_codigo: number;
  produto_nome: string;
  tipo_combustivel: string;
  estoque_atual_litros: number;
  capacidade_tanque: number;
  ocupacao_percentual: number;
  consumo_medio_diario: number;
  dias_cobertura_desejado: number;
  lead_time_horas: number;
  autonomia_horas_restantes: number;
  autonomia_dias_restantes: number;
  status_alerta: "OK" | "ATENCAO" | "COMPRA_URGENTE";
  sugestao_compra_litros: number;
  alerta_label?: string;
  dias_historico_usado: number;
  observacoes: string[];
  cpm_rs_litro?: number;
  preco_venda_rs_litro?: number;
  margem_bruta_rs_litro?: number;
  valor_estoque_imobilizado_rs?: number;
  cpm_origem?: string;
}

export interface InventoryPredictionResponse {
  success: boolean;
  empresa_codigo: number;
  empresa_nome: string;
  data_calculo: string;
  dias_cobertura: number;
  lead_time_horas: number;
  predicoes: TankPrediction[];
  total_sugestao_compra_litros: number;
  tanques_com_alerta: number;
  tanques_urgentes: number;
  observacoes: string[];
}

/** Inteligência Integrada — GET /api/v1/executive/sales/composition */
export interface SalesCompositionSummary {
  faturamentoTotal: number;
  faturamentoCombustivel: number;
  faturamentoProdutosPista: number;
  faturamentoConveniencia: number;
  litrosVendidos: number;
  quantidadeAbastecimentos: number;
  clientesLoja: number;
  ticketMedioAbastecimento: number;
  receitaNaoCombustivelPorAbastecimento: number;
  litrosPorAbastecimento: number;
  penetracaoProdutosPistaPercentual: number;
  penetracaoConvenienciaPercentual: number;
  penetracaoCrossSellingPercentual: number;
}

export interface SalesCompositionSector {
  setor: "Combustíveis" | "Produtos de Pista" | "Conveniência" | string;
  faturamento: number;
  margem: number;
  participacao: number;
}

export interface SalesCrossSellingFunnel {
  totalAbastecimentos: number;
  clientesLoja: number;
  transacoesCombustivelProdutoPista: number;
  transacoesCombustivelConveniencia: number;
  transacoesCombustivelComboTotal: number;
  penetracaoProdutosPistaPercentual: number;
  penetracaoConvenienciaPercentual: number;
  penetracaoTotalPercentual: number;
  relacaoLojaPistaPercentual: number;
}

export interface SalesCompositionBreakdownItem {
  categoria: string;
  litros?: number;
  faturamento: number;
  participacao: number;
}

export interface SalesCompositionResponse {
  summary: SalesCompositionSummary;
  compositionBySector: SalesCompositionSector[];
  crossSellingFunnel: SalesCrossSellingFunnel;
  combustiveis?: SalesCompositionBreakdownItem[];
  produtosPista?: SalesCompositionBreakdownItem[];
  conveniencia?: SalesCompositionBreakdownItem[];
  empresaCodigo?: number | null;
  periodo?: { inicio: string; fim: string };
  fonteAbastecimentos?: string;
  fallback?: boolean;
  mensagem?: string | null;
}

/** Sprint 60 — Painel de Aferição / Drill-down despesas */
export interface ExpenseDetailItem {
  id?: string;
  numeroDocumento?: string;
  numeroNF?: string;
  descricao?: string;
  historico?: string;
  fornecedor?: string;
  favorecido?: string;
  categoria?: string;
  categoriaLabel?: string;
  valor?: number;
  dataPagamento?: string;
  dataVencimento?: string;
  planoConta?: string;
  planoContaCodigo?: number | null;
  planoContaHierarquia?: string;
  planoContaOficial?: string;
  planoContaTipo?: string;
  grupoConta?: string;
  grupoContaCodigo?: number | null;
  centroCusto?: string;
  centroCustoCodigo?: number | null;
  empresaCodigo?: number;
}

export interface ExpenseDetailsResponse {
  empresaCodigo?: number | null;
  empresaNome?: string;
  periodo?: { inicio: string; fim: string };
  categoria?: string;
  categoriaKey?: string;
  subtotal?: number;
  quantidade?: number;
  itens?: ExpenseDetailItem[];
  success?: boolean;
  mensagem?: string | null;
}

export interface DataAuditExpenseCategory {
  categoria: string;
  categoriaKey?: string;
  valor: number;
  qtd_lancamentos: number;
  itens?: ExpenseDetailItem[];
}

export interface DataAuditValeItem {
  descricao?: string;
  funcionario?: string;
  valor?: number;
  planoConta?: string;
  planoContaCodigo?: number | null;
  fonte?: string;
}

export interface DataAuditValesFuncionarios {
  total: number;
  quantidade: number;
  itens: DataAuditValeItem[];
}

export interface DataAuditFilial {
  empresaCodigo: number;
  empresaNome: string;
  faturamentoTotal: number;
  volumeLitros: number;
  quantidadeAbastecimentos: number;
  ocupacaoTanquesPct: number;
  despesasTotal: number;
  despesasPorCategoria: DataAuditExpenseCategory[];
  valesFuncionarios?: DataAuditValesFuncionarios;
  resultadoOperacionalDiario: number;
  margemBrutaMediaRsLitro: number;
  valorEstoqueImobilizado: number;
  fallback?: boolean;
  mensagem?: string | null;
}

export interface DataAuditResponse {
  periodo: { inicio: string; fim: string };
  filiais: DataAuditFilial[];
  consolidado: Record<string, number | string>;
  success?: boolean;
  mensagem?: string;
}

/** Sprint 7 — Análise consolidada de unidades */
export type UnitsStatusOperacional = "EXCELENTE" | "ATENCAO" | "CRITICO" | string;

export interface UnitsPerformanceCategoria {
  categoria: string;
  categoriaKey: string;
  valor: number;
  qtd_lancamentos: number;
}

export interface UnitsPerformanceUnidade {
  unidade_id: number;
  nome_unidade: string;
  galonagem_litros: number;
  faturamento_total_rs: number;
  despesas_totais_rs: number;
  diferenca_lucro_rs: number;
  resultado_operacional_rs: number;
  margem_percentual: number;
  margem_operacional_pct: number;
  status_operacional: UnitsStatusOperacional;
  folha_pagamento_rs: number;
  qtd_funcionarios?: number | null;
  qtd_abastecimentos?: number;
  ticket_medio_rs?: number;
  ticket_medio_tipo?: string;
  crescimento_faturamento_pct?: number | null;
  crescimento_galonagem_pct?: number | null;
  crescimento_despesas_pct?: number | null;
  crescimento_margem_pp?: number | null;
  despesas_por_categoria?: UnitsPerformanceCategoria[];
}

export interface UnitsPerformanceRede {
  faturamento_total_rs: number;
  despesas_totais_rs: number;
  lucro_liquido_global_rs: number;
  resultado_operacional_rs: number;
  margem_media_pct: number;
  galonagem_total_litros: number;
  status_operacional?: UnitsStatusOperacional;
}

export interface UnitsPerformanceResponse {
  success?: boolean;
  periodo: { inicio: string; fim: string };
  periodo_anterior?: { inicio: string; fim: string };
  parametros?: {
    meta_margem_pct: number;
    limite_atencao_pct: number;
    metrica?: string;
    formula?: string;
  };
  rede: UnitsPerformanceRede;
  unidades: UnitsPerformanceUnidade[];
  ranking_mais_lucrativas?: Array<{
    unidade_id: number;
    nome_unidade: string;
    resultado_operacional_rs: number;
    margem_operacional_pct: number;
  }>;
  ranking_maior_risco?: Array<{
    unidade_id: number;
    nome_unidade: string;
    margem_operacional_pct: number;
    status_operacional: string;
  }>;
  insights?: string[];
  desvios_categoria?: Array<{
    unidade_id: number;
    nome_unidade: string;
    categoria: string;
    valor_rs: number;
    media_rede_rs: number;
    desvio_pct: number;
    mensagem: string;
  }>;
  grafico_barras?: Array<{
    unidade_id: number;
    nome: string;
    faturamento: number;
    despesas: number;
    resultado: number;
    galonagem: number;
  }>;
  gerado_em?: string;
  mensagem?: string;
}

export interface UnitsPerformanceDetailResponse {
  success?: boolean;
  periodo: { inicio: string; fim: string };
  unidade: UnitsPerformanceUnidade;
  evolucao_mensal: Array<{
    mes: string;
    label: string;
    galonagem_litros: number;
    faturamento_total_rs: number;
    despesas_totais_rs?: number | null;
    resultado_operacional_rs?: number | null;
    margem_operacional_pct?: number | null;
  }>;
  despesas_por_categoria: UnitsPerformanceCategoria[];
  desvios?: Array<{
    categoria: string;
    valor_rs: number;
    media_rede_rs: number;
    desvio_pct: number;
    mensagem: string;
  }>;
  insights?: string[];
  rede_resumo?: UnitsPerformanceRede;
  mensagem?: string;
}

/** Rush Intelligence V3 — Mapa de Calor Operacional */
export interface RushHeatmapCard {
  type: string;
  severity: string;
  subject_type: string;
  subject_id: string;
  subject_name: string;
  heat_score: number;
  evidence?: Record<string, unknown> & {
    comparativo_absoluto?: string;
    nota?: string;
  };
  recurrence?: number;
  recommendation: string;
}

export interface RushHeatmapPost {
  unidade_id: number;
  nome_unidade: string;
  rush_status?: {
    active: boolean;
    label: string;
    start: string;
    end: string;
    abastecimentos: number;
  };
  heat_score: number;
  heat_color: string;
  forecourt_imbalance_score: number;
  island_pressure?: Array<{
    ilha: number;
    capacidade_bicos: number;
    bicos_ocupados_proxy: number;
    abastecimentos_janela: number;
    utilizacao: number;
    frentistas?: string[];
  }>;
  ranking_absoluto?: Array<{
    pos: number;
    frentista_id?: number | null;
    frentista_nome: string;
    abastecimentos: number;
    litros: number;
    valor_rs: number;
    comparativo: string;
  }>;
  ranking_relativo?: Array<{
    pos: number;
    frentista_id?: number | null;
    frentista_nome: string;
    abastecimentos_hora: number;
    litros_hora: number;
    tma_minutos: number;
    minutos_ativos: number;
    participacao_equipe_pct: number;
  }>;
  suspeitas?: RushHeatmapCard[];
  drilldown?: {
    posto: number;
    ilhas: number[];
    frentistas: string[];
    periodo: string;
    historico_recorrencia: Record<string, number>;
  };
}

export interface RushHeatmapResponse {
  success?: boolean;
  fonte?: string;
  data_audit?: Record<string, string>;
  latency_ms?: number;
  periodo_analise?: {
    inicio: string;
    fim: string;
    label: string;
    modo?: string;
  };
  rush_status?: {
    posts_com_rush: number;
    total_suspeitas: number;
    modo?: string;
  };
  heat_score_rede?: number;
  forecourt_imbalance_score_rede?: number;
  posts: RushHeatmapPost[];
  intelligence_cards: RushHeatmapCard[];
  regras?: Record<string, string>;
  mensagem?: string;
}

export interface AuditFraudSettings {
  empresa_id: number;
  tempo_retencao_critico_min: number;
  tempo_retencao_atencao_min: number;
  tempo_agrupamento_max_min: number;
  percentual_desconto_suspeito_pct: number;
  recorrencia_cpf_cartao_limite: number;
  updated_at?: string | null;
  fonte?: string;
}

export interface CardFraudBicoDetalhe {
  abastecimentoId?: number;
  idAbastecimento?: number;
  uuid?: string;
  bico: number;
  bomba?: number;
  horaBico?: string;
  dataHoraBico?: string;
  produto?: string;
  tipoCombustivel?: string;
  postoNome?: string;
  litros: number;
  precoUnitario?: number;
  precoTabela?: number;
  precoPraticado?: number;
  valor?: number;
  valorTotal?: number;
  valorDesconto?: number;
  descontoPorLitro?: number;
  origemDesconto?: string;
  cpfDesconto?: string | null;
  tempoRetencaoMinutos?: number;
}

export interface FraudRankingItem {
  nome: string;
  qtd: number;
  valor: number;
}

/** Auditoria de Caixas — GET /api/v1/executive/audit/cashier (cache RAM) */
export interface CashierAuditResumo {
  totalEsperado: number;
  totalDeclarado: number;
  divergenciaTotal: number;
  sobras: number;
  faltas: number;
  qtdTurnos?: number;
  qtdAuditados?: number;
  qtdPendentes?: number;
  qtdComDivergencia?: number;
}

export interface CashierAuditFechamento {
  id: string;
  operadorId?: number | null;
  operadorNome: string;
  postoCodigo: number;
  postoNome: string;
  turno: string;
  dataRef: string;
  faturamentoBico: number;
  faturamentoCaixa: number;
  saldo: number;
  status: "AUDITADO" | "PENDENTE" | string;
  qtdAbastecimentos: number;
  caixaCodigo?: number | null;
}

export interface CashierAuditQuebraForma {
  forma: string;
  label: string;
  valorSistemico: number;
  valorInformado: number;
  diferenca: number;
}

export interface CashierAuditResponse {
  success?: boolean;
  fromCache?: boolean;
  dataRef?: string;
  geradoEm?: string;
  latencyMs?: number;
  resumoDia: CashierAuditResumo;
  fechamentosPorTurno: CashierAuditFechamento[];
  quebrasPorFormaPagamento: CashierAuditQuebraForma[];
  observacoes?: string[];
  pagina?: number;
  limite?: number;
  totalFechamentos?: number;
  hasMore?: boolean;
}

/** Painel Tático — GET /api/v1/executive/audit/pista-live */
export interface PistaLiveBico {
  bico: number;
  bomba: number;
  ilha: number;
  status: "NORMAL" | "RETENCAO" | string;
  idAbastecimento: number;
  uuid?: string;
  empresaCodigo: number;
  empresaNome: string;
  dataHoraT1: string;
  valorPendente: number;
  valorUltimo: number;
  litros: number;
  produto: string;
  frentistaNome: string;
  frentistaId?: number | null;
  tempoRetencaoMinutos: number;
  formaPagamento?: string;
  ocorrenciaId?: string | null;
  scoreGravidade?: number | null;
  cartaoRepetido?: boolean;
}

export interface PistaLiveBomba {
  bomba: number;
  bicos: PistaLiveBico[];
  retencoes: number;
}

export interface PistaLiveIlha {
  ilha: number;
  label: string;
  bombas: PistaLiveBomba[];
  retencoes: number;
}

export interface PistaLiveFilial {
  empresaCodigo: number;
  empresaNome: string;
  ilhas: PistaLiveIlha[];
  totalBicos: number;
  totalRetencoes: number;
}

export interface PistaLiveResponse {
  success?: boolean;
  fromCache?: boolean;
  fonte?: string;
  dataRef?: string;
  ultimaSincronizacaoIso?: string | null;
  syncing?: boolean;
  empresaCodigo?: number | null;
  totalBicos: number;
  totalRetencoes: number;
  filiais: PistaLiveFilial[];
  observacoes?: string[];
}

export interface CardFraudOcorrencia {
  id: string;
  idOcorrencia?: string;
  linkOcorrencia?: string;
  gatilho: "TIME_GAP" | "AGRUPAMENTO_LOTE" | "AMBOS" | string;
  frentistaId: number | null;
  frentistaNome: string;
  funcionarioNome?: string;
  funcionarioId?: number | null;
  empresaCodigo: number;
  empresaNome: string;
  postoNome?: string;
  postoUnidade?: number;
  vendaCodigo: number;
  uuid?: string;
  horaBico?: string;
  horaBaixa?: string;
  dataHora?: string;
  dataHoraBaixa?: string;
  dataHoraBico?: string;
  dataHoraEmissaoCupom?: string;
  horaPrimeiroBico?: string;
  horaUltimoBico?: string;
  horaBaixaCartao?: string;
  tempoRetencaoMinutos: number;
  intervaloBicosMinutos: number;
  qtdAbastecimentosAgrupados: number;
  valorTotalCartao: number;
  valorTotal?: number;
  nivelRisco:
    | "ATENCAO"
    | "CRITICO"
    | "ALTO"
    | "DESCONTO"
    | "MEDIO"
    | "BAIXO"
    | string;
  nivelRiscoLegado?: string;
  scoreGravidade?: number;
  meioPagamento: string;
  formaPagamento?: string;
  cartaoBandeira?: string;
  cartaoFinal?: string;
  cartaoNsu?: string;
  cartaoAutorizacao?: string;
  isEspecie?: boolean;
  tipoCombustivel?: string;
  litros?: number;
  precoUnitario?: number;
  valorDesconto?: number;
  descontoPorLitro?: number;
  percentualDesconto?: number;
  origemDesconto?: string;
  cpfDesconto?: string | null;
  cpfRepetido?: boolean;
  /** Cartão Curinga — mesmo Bandeira+Final/NSU em >1 baixa */
  cartaoRepetido?: boolean;
  cartao_repetido?: boolean;
  quantidadeUsoCartao?: number;
  quantidade_uso_cartao?: number;
  quantidadeAbastecimentosCartao?: number;
  motivoSuspeita?: string;
  isAgrupado?: boolean;
  abastecimentosAgrupados?: CardFraudBicoDetalhe[];
  metricasAgrupamento?: {
    qtdAbastecimentos: number;
    intervaloBicosMinutos: number;
    tempoRetencaoMinutos: number;
    limiarCriticoMin: number;
    limiarAtencaoMin: number;
    limiarAgrupamentoMin: number;
  };
  detalhes: CardFraudBicoDetalhe[];
}

export interface CardFraudResumo {
  totalAgrupamentosSuspeitos: number;
  totalCriticos: number;
  totalAtencao: number;
  valorTotalRetidoCartoes: number;
  valorCritico: number;
  frentistaMaiorIncidencia: string;
  frentistaMaiorIncidenciaQtd: number;
  abastecimentosCriticosBanner: number;
  totalFraudes?: number;
  valorTotalEnvolvido?: number;
  totalDescontosIdentificados?: number;
  totalAbastecimentosSuspeitos?: number;
  rankingFrentistas?: FraudRankingItem[];
  rankingCartoes?: FraudRankingItem[];
  rankingCPFs?: FraudRankingItem[];
  rankingPostos?: FraudRankingItem[];
  distribuicaoRisco?: Record<string, number>;
}

export interface CardFraudFrentistaOption {
  id: number | null;
  nome: string;
  qtd: number;
}

export type CardFraudTipoInfracao =
  | ""
  | "RETENCAO_CARTAO"
  | "EXCESSO_DESCONTO"
  | "AGRUPAMENTO_BICOS"
  | "ABUSO_CPF";

export type CardFraudFormaPagamentoFiltro =
  | ""
  | "CARTAO"
  | "PIX"
  | "DINHEIRO"
  | "FROTA";

export interface CardFraudFiltros {
  frentista_id?: number | null;
  frentista_nome?: string;
  tipo_infracao?: CardFraudTipoInfracao | string;
  tempo_retencao_min?: number | null;
  forma_pagamento?: CardFraudFormaPagamentoFiltro | string;
  busca_texto?: string;
  filial_id?: number | null;
}

export interface CardFraudAuditResponse {
  success: boolean;
  synthetic: boolean;
  fromCache?: boolean;
  fonte: string;
  endpoint: string;
  periodo: { inicio: string; fim: string };
  dataRef?: string;
  geradoEm?: string | null;
  latencyMs?: number;
  filterLatencyMs?: number;
  empresaCodigo?: number | null;
  limiarRetencaoMinutos: number;
  limiarCriticoMinutos: number;
  parametros?: AuditFraudSettings;
  resumo: CardFraudResumo;
  resumoExecutivo?: CardFraudResumo;
  ocorrencias: CardFraudOcorrencia[];
  bannerAlerta: string | null;
  observacoes: string[];
  totalOcorrencias?: number;
  totalFiltrado?: number;
  frentistasDisponiveis?: CardFraudFrentistaOption[];
  filtrosAplicados?: CardFraudFiltros;
}

/** FORECOURT-CONFIG — layout operacional da pista */
export interface ForecourtNozzleLink {
  nozzle_id: number;
  active?: boolean;
  label?: string;
}

export interface ForecourtZone {
  code: string;
  name?: string;
  display_order?: number;
  x?: number | null;
  y?: number | null;
  width?: number | null;
  height?: number | null;
}

export interface ForecourtMarker {
  code: string;
  label?: string;
  x: number;
  y: number;
}

export interface ForecourtIsland {
  id?: string;
  code: string;
  name?: string;
  zone_code?: string;
  display_order?: number;
  x: number;
  y: number;
  width: number;
  height: number;
  active?: boolean;
}

export interface ForecourtPosition {
  id?: string;
  island_code: string;
  island_id?: string;
  pump_id: number;
  pump_name?: string;
  code: string;
  name?: string;
  orientation: string;
  x: number;
  y: number;
  active?: boolean;
  operational?: boolean;
  nozzles: ForecourtNozzleLink[];
}

export interface ForecourtLayoutSummary {
  layout_id?: string;
  name?: string;
  station_id?: number;
  version?: number | string;
  status?: string;
  mapping_status?: string;
  mapping_note?: string;
  qtd_zonas?: number;
  qtd_ilhas: number;
  qtd_ilhas_liquidos?: number;
  qtd_equip_gnv?: number;
  qtd_bombas: number;
  qtd_bombas_liquidos?: number;
  qtd_posicoes: number;
  qtd_posicoes_liquidos?: number;
  qtd_bicos: number;
}

export interface ForecourtLayout {
  id: string;
  station_id: number;
  version: number;
  name: string;
  status: string;
  mapping_status: string;
  mapping_note?: string;
  coordinate_width: number;
  coordinate_height: number;
  zones?: ForecourtZone[];
  markers?: ForecourtMarker[];
  islands: ForecourtIsland[];
  positions: ForecourtPosition[];
  summary?: ForecourtLayoutSummary;
  seeded?: boolean;
  seed_id?: string;
  created_at?: string;
  updated_at?: string;
}
