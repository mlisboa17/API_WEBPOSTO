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

export interface Block9Anomalias {
  titulo: string;
  status: string;
  divergencias_caixa: ReconciliationSummary;
  detalhamento_pagamento: Array<{ natureza: string; valor: string; transacoes: number }>;
  rombo_por_operador_turno: CashHoleDetail[];
  alertas: Array<Record<string, unknown>>;
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
