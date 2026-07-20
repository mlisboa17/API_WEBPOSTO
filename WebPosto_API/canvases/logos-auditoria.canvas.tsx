import React from "react";
import {
  Stack,
  Row,
  Grid,
  Spacer,
  H1,
  H2,
  H3,
  Text,
  Code,
  Callout,
  Pill,
  Stat,
  Table,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Select,
  Button,
  useCanvasState,
  useHostTheme,
  mergeStyle
} from "cursor/canvas";

// ============================================================================
// SIMULAÇÃO DE DADOS BASEADA NAS CLASSES PYDANTIC (auditoria_models.py)
// ============================================================================

interface DespesaCaixaSimulada {
  id: string;
  unidade_id: string;
  caixa_tipo: "pista" | "conveniencia" | "restaurante";
  horario: string;
  categoria: string; // Vazia ou nula indica "Sem Categoria"
  valor: number;
  operador: string;
  descricao?: string;
  status_justificativa: "pendente" | "justificada" | "rejeitada" | "em_analise";
  tem_documento: boolean;
}

interface MovimentacaoEspecieSimulada {
  especie: "Dinheiro" | "PIX" | "Cartão Débito" | "Cartão Crédito" | "Frotistas/Prazo";
  valor_esperado: number;
  valor_informado: number;
}

interface FechamentoCaixaSimulado {
  id: string;
  unidade_id: string;
  caixa_tipo: "pista" | "conveniencia" | "restaurante";
  horario_abertura: string;
  horario_fechamento: string;
  faturamento_bruto: number;
  despesas_caixa_total: number;
  movimentacoes: MovimentacaoEspecieSimulada[];
  saldo_esperado_dinheiro: number;
  saldo_informado_dinheiro: number;
  status: "aberto" | "fechado" | "consolidado" | "em_auditoria";
  operador_fechamento: string;
}

// Banco de dados simulado contendo dados para as 3 unidades (Real, Casa Caiada, VIP)
const SIMULATED_DATA: Record<string, {
  fechamentos: FechamentoCaixaSimulado[];
  despesas: DespesaCaixaSimulada[];
  meta: {
    media_historica_despesas_percentual: number; // Padrão histórico de 5%
  }
}> = {
  "Real": {
    meta: { media_historica_despesas_percentual: 5.0 },
    fechamentos: [
      {
        id: "FECH-R01",
        unidade_id: "Real",
        caixa_tipo: "pista",
        horario_abertura: "06:00",
        horario_fechamento: "14:00",
        faturamento_bruto: 18450.00,
        despesas_caixa_total: 120.00,
        saldo_esperado_dinheiro: 3250.00,
        saldo_informado_dinheiro: 3242.00, // Diferença R$ 8.00 (Dentro do limite de R$ 10.00)
        status: "consolidado",
        operador_fechamento: "Carlos Santos",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 3250.00, valor_informado: 3242.00 },
          { especie: "PIX", valor_esperado: 4800.00, valor_informado: 4800.00 },
          { especie: "Cartão Débito", valor_esperado: 3500.00, valor_informado: 3500.00 },
          { especie: "Cartão Crédito", valor_esperado: 5400.00, valor_informado: 5400.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 1500.00, valor_informado: 1500.00 }
        ]
      },
      {
        id: "FECH-R02",
        unidade_id: "Real",
        caixa_tipo: "pista",
        horario_abertura: "14:00",
        horario_fechamento: "22:00",
        faturamento_bruto: 21900.00,
        despesas_caixa_total: 450.00,
        saldo_esperado_dinheiro: 4120.00,
        saldo_informado_dinheiro: 4085.00, // Quebra R$ 35.00 (Acima de R$ 10.00 - Alerta Vermelho!)
        status: "fechado",
        operador_fechamento: "Ana Paula Silva",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 4120.00, valor_informado: 4085.00 },
          { especie: "PIX", valor_esperado: 6200.00, valor_informado: 6200.00 },
          { especie: "Cartão Débito", valor_esperado: 4400.00, valor_informado: 4400.00 },
          { especie: "Cartão Crédito", valor_esperado: 5180.00, valor_informado: 5180.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 2000.00, valor_informado: 2000.00 }
        ]
      },
      {
        id: "FECH-R03",
        unidade_id: "Real",
        caixa_tipo: "conveniencia",
        horario_abertura: "08:00",
        horario_fechamento: "20:00",
        faturamento_bruto: 6800.00,
        despesas_caixa_total: 85.00,
        saldo_esperado_dinheiro: 1150.00,
        saldo_informado_dinheiro: 1150.00, // Perfeito
        status: "consolidado",
        operador_fechamento: "Renato Melo",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 1150.00, valor_informado: 1150.00 },
          { especie: "PIX", valor_esperado: 2400.00, valor_informado: 2400.00 },
          { especie: "Cartão Débito", valor_esperado: 1250.00, valor_informado: 1250.00 },
          { especie: "Cartão Crédito", valor_esperado: 2000.00, valor_informado: 2000.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 0.00, valor_informado: 0.00 }
        ]
      },
      {
        id: "FECH-R04",
        unidade_id: "Real",
        caixa_tipo: "restaurante",
        horario_abertura: "11:00",
        horario_fechamento: "16:00",
        faturamento_bruto: 4500.00,
        despesas_caixa_total: 0.00,
        saldo_esperado_dinheiro: 850.00,
        saldo_informado_dinheiro: 850.00,
        status: "aberto", // Ainda não consolidado! (Alerta Laranja)
        operador_fechamento: "Marcos Souza",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 850.00, valor_informado: 850.00 },
          { especie: "PIX", valor_esperado: 1550.00, valor_informado: 1550.00 },
          { especie: "Cartão Débito", valor_esperado: 900.00, valor_informado: 900.00 },
          { especie: "Cartão Crédito", valor_esperado: 1200.00, valor_informado: 1200.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 0.00, valor_informado: 0.00 }
        ]
      }
    ],
    despesas: [
      { id: "EXP-R01", unidade_id: "Real", caixa_tipo: "pista", horario: "09:15", categoria: "Gelo", valor: 60.00, operador: "Carlos Santos", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-R02", unidade_id: "Real", caixa_tipo: "pista", horario: "11:30", categoria: "Insumos", valor: 45.00, operador: "Carlos Santos", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-R03", unidade_id: "Real", caixa_tipo: "conveniencia", horario: "13:20", categoria: "Vale Operador", valor: 50.00, operador: "Renato Melo", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-R04", unidade_id: "Real", caixa_tipo: "pista", horario: "15:40", categoria: "Limpeza", valor: 120.00, operador: "Ana Paula Silva", status_justificativa: "pendente", tem_documento: false }, // Sem anexo! Vermelho!
      { id: "EXP-R05", unidade_id: "Real", caixa_tipo: "pista", horario: "17:10", categoria: "", valor: 180.00, operador: "Ana Paula Silva", status_justificativa: "em_analise", tem_documento: true }, // Sem Categoria! Vermelho!
      { id: "EXP-R06", unidade_id: "Real", caixa_tipo: "pista", horario: "20:05", categoria: "Manutenção", valor: 150.00, operador: "Ana Paula Silva", status_justificativa: "justificada", tem_documento: true }
    ]
  },
  "Casa Caiada": {
    meta: { media_historica_despesas_percentual: 5.0 },
    fechamentos: [
      {
        id: "FECH-C01",
        unidade_id: "Casa Caiada",
        caixa_tipo: "pista",
        horario_abertura: "06:00",
        horario_fechamento: "14:00",
        faturamento_bruto: 14200.00,
        despesas_caixa_total: 80.00,
        saldo_esperado_dinheiro: 2100.00,
        saldo_informado_dinheiro: 2100.00,
        status: "consolidado",
        operador_fechamento: "Eduardo Rocha",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 2100.00, valor_informado: 2100.00 },
          { especie: "PIX", valor_esperado: 4100.00, valor_informado: 4100.00 },
          { especie: "Cartão Débito", valor_esperado: 2800.00, valor_informado: 2800.00 },
          { especie: "Cartão Crédito", valor_esperado: 3700.00, valor_informado: 3700.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 1500.00, valor_informado: 1500.00 }
        ]
      },
      {
        id: "FECH-C02",
        unidade_id: "Casa Caiada",
        caixa_tipo: "pista",
        horario_abertura: "14:00",
        horario_fechamento: "22:00",
        faturamento_bruto: 16800.00,
        despesas_caixa_total: 190.00,
        saldo_esperado_dinheiro: 2800.00,
        saldo_informado_dinheiro: 2795.00, // Quebra R$ 5.00 (Dentro do limite)
        status: "consolidado",
        operador_fechamento: "Juliana Mendes",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 2800.00, valor_informado: 2795.00 },
          { especie: "PIX", valor_esperado: 4900.00, valor_informado: 4900.00 },
          { especie: "Cartão Débito", valor_esperado: 3200.00, valor_informado: 3200.00 },
          { especie: "Cartão Crédito", valor_esperado: 4100.00, valor_informado: 4100.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 1800.00, valor_informado: 1800.00 }
        ]
      },
      {
        id: "FECH-C03",
        unidade_id: "Casa Caiada",
        caixa_tipo: "conveniencia",
        horario_abertura: "08:00",
        horario_fechamento: "20:00",
        faturamento_bruto: 5100.00,
        despesas_caixa_total: 50.00,
        saldo_esperado_dinheiro: 920.00,
        saldo_informado_dinheiro: 918.00, // Quebra R$ 2.00
        status: "consolidado",
        operador_fechamento: "Aline Bastos",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 920.00, valor_informado: 918.00 },
          { especie: "PIX", valor_esperado: 1680.00, valor_informado: 1680.00 },
          { especie: "Cartão Débito", valor_esperado: 1100.00, valor_informado: 1100.00 },
          { especie: "Cartão Crédito", valor_esperado: 1400.00, valor_informado: 1400.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 0.00, valor_informado: 0.00 }
        ]
      }
    ],
    despesas: [
      { id: "EXP-C01", unidade_id: "Casa Caiada", caixa_tipo: "pista", horario: "10:10", categoria: "Gelo", valor: 50.00, operador: "Eduardo Rocha", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-C02", unidade_id: "Casa Caiada", caixa_tipo: "pista", horario: "13:00", categoria: "Outros", valor: 30.00, operador: "Eduardo Rocha", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-C03", unidade_id: "Casa Caiada", caixa_tipo: "pista", horario: "16:45", categoria: "Insumos", valor: 120.00, operador: "Juliana Mendes", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-C04", unidade_id: "Casa Caiada", caixa_tipo: "pista", horario: "18:15", categoria: "Luz", valor: 70.00, operador: "Juliana Mendes", status_justificativa: "pendente", tem_documento: false }, // Sem anexo! Vermelho!
      { id: "EXP-C05", unidade_id: "Casa Caiada", caixa_tipo: "conveniencia", horario: "19:00", categoria: "Vale Operador", valor: 50.00, operador: "Aline Bastos", status_justificativa: "justificada", tem_documento: true }
    ]
  },
  "VIP": {
    meta: { media_historica_despesas_percentual: 5.0 },
    fechamentos: [
      {
        id: "FECH-V01",
        unidade_id: "VIP",
        caixa_tipo: "pista",
        horario_abertura: "06:00",
        horario_fechamento: "14:00",
        faturamento_bruto: 24500.00,
        despesas_caixa_total: 1850.00, // Alto índice de despesas!
        saldo_esperado_dinheiro: 4100.00,
        saldo_informado_dinheiro: 4055.00, // Quebra R$ 45.00 (Acima de R$ 10.00 - Vermelho)
        status: "fechado",
        operador_fechamento: "Lucas Lima",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 4100.00, valor_informado: 4055.00 },
          { especie: "PIX", valor_esperado: 7500.00, valor_informado: 7500.00 },
          { especie: "Cartão Débito", valor_esperado: 4800.00, valor_informado: 4800.00 },
          { especie: "Cartão Crédito", valor_esperado: 6100.00, valor_informado: 6100.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 2000.00, valor_informado: 2000.00 }
        ]
      },
      {
        id: "FECH-V02",
        unidade_id: "VIP",
        caixa_tipo: "pista",
        horario_abertura: "14:00",
        horario_fechamento: "22:00",
        faturamento_bruto: 29000.00,
        despesas_caixa_total: 2100.00, // Altíssimo desvio!
        saldo_esperado_dinheiro: 5200.00,
        saldo_informado_dinheiro: 5120.00, // Quebra R$ 80.00 (Vermelho)
        status: "fechado",
        operador_fechamento: "Bruna Martins",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 5200.00, valor_informado: 5120.00 },
          { especie: "PIX", valor_esperado: 9200.00, valor_informado: 9200.00 },
          { especie: "Cartão Débito", valor_esperado: 5800.00, valor_informado: 5800.00 },
          { especie: "Cartão Crédito", valor_esperado: 6800.00, valor_informado: 6800.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 2000.00, valor_informado: 2000.00 }
        ]
      },
      {
        id: "FECH-V03",
        unidade_id: "VIP",
        caixa_tipo: "conveniencia",
        horario_abertura: "08:00",
        horario_fechamento: "20:00",
        faturamento_bruto: 9200.00,
        despesas_caixa_total: 350.00,
        saldo_esperado_dinheiro: 1850.00,
        saldo_informado_dinheiro: 1850.00,
        status: "consolidado",
        operador_fechamento: "Patricia Costa",
        movimentacoes: [
          { especie: "Dinheiro", valor_esperado: 1850.00, valor_informado: 1850.00 },
          { especie: "PIX", valor_esperado: 2900.00, valor_informado: 2900.00 },
          { especie: "Cartão Débito", valor_esperado: 1800.00, valor_informado: 1800.00 },
          { especie: "Cartão Crédito", valor_esperado: 2650.00, valor_informado: 2650.00 },
          { especie: "Frotistas/Prazo", valor_esperado: 0.00, valor_informado: 0.00 }
        ]
      }
    ],
    despesas: [
      { id: "EXP-V01", unidade_id: "VIP", caixa_tipo: "pista", horario: "08:30", categoria: "Combustível", valor: 450.00, operador: "Lucas Lima", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-V02", unidade_id: "VIP", caixa_tipo: "pista", horario: "10:45", categoria: "Manutenção", valor: 1200.00, operador: "Lucas Lima", status_justificativa: "em_analise", tem_documento: true },
      { id: "EXP-V03", unidade_id: "VIP", caixa_tipo: "pista", horario: "12:15", categoria: "Gelo", valor: 200.00, operador: "Lucas Lima", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-V04", unidade_id: "VIP", caixa_tipo: "pista", horario: "15:20", categoria: "Insumos", valor: 850.00, operador: "Bruna Martins", status_justificativa: "pendente", tem_documento: false }, // Sem documento! Vermelho!
      { id: "EXP-V05", unidade_id: "VIP", caixa_tipo: "pista", horario: "16:40", categoria: "", valor: 550.00, operador: "Bruna Martins", status_justificativa: "pendente", tem_documento: false }, // Sem categoria & documento! Vermelho!
      { id: "EXP-V06", unidade_id: "VIP", caixa_tipo: "pista", horario: "19:10", categoria: "Limpeza", valor: 700.00, operador: "Bruna Martins", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-V07", unidade_id: "VIP", caixa_tipo: "conveniencia", horario: "13:50", categoria: "Vale Operador", valor: 150.00, operador: "Patricia Costa", status_justificativa: "justificada", tem_documento: true },
      { id: "EXP-V08", unidade_id: "VIP", caixa_tipo: "conveniencia", horario: "17:15", categoria: "Insumos", valor: 200.00, operador: "Patricia Costa", status_justificativa: "justificada", tem_documento: true }
    ]
  }
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export default function LogosAuditoriaDashboard(): JSX.Element {
  const hostTheme = useHostTheme();
  const isDark = hostTheme.kind === "dark";

  // Estados persistentes no Canvas
  const [selectedUnidade, setSelectedUnidade] = useCanvasState<string>("selectedUnidade", "Real");
  const [selectedDate, setSelectedDate] = useCanvasState<string>("selectedDate", "2026-07-03");
  const [onlyAlerts, setOnlyAlerts] = useCanvasState<boolean>("onlyAlerts", false);
  const [selectedCaixaId, setSelectedCaixaId] = useCanvasState<string | null>("selectedCaixaId", null);

  // Recupera dados com base na unidade selecionada
  const activeUnitData = SIMULATED_DATA[selectedUnidade] || SIMULATED_DATA["Real"];
  const fechamentos = activeUnitData.fechamentos;
  const despesas = activeUnitData.despesas;

  // Filtragem opcional por caixa específico clicado
  const filteredDespesas = despesas.filter((d) => {
    // Se o filtro "Apenas alertas" estiver ativado, filtra despesas sem categoria ou sem documento
    const fitsAlert = onlyAlerts ? (!d.categoria || !d.tem_documento) : true;
    if (selectedCaixaId) {
      const caixa = fechamentos.find((f) => f.id === selectedCaixaId);
      const fitsCaixa = caixa ? d.caixa_tipo === caixa.caixa_tipo : true;
      return fitsCaixa && fitsAlert;
    }
    return fitsAlert;
  });

  // ============================================================================
  // CÁLCULOS E CONSOLIDAÇÃO (Equivalente à lógica Pydantic)
  // ============================================================================

  const faturamentoTotal = fechamentos.reduce((sum, f) => sum + f.faturamento_bruto, 0);
  const despesasOperacionais = despesas.reduce((sum, d) => sum + d.valor, 0);
  
  // Saldo em Espécie (dinheiro) total esperado vs informado de todos os caixas
  const saldoDinheiroEsperado = fechamentos.reduce((sum, f) => sum + f.saldo_esperado_dinheiro, 0);
  const saldoDinheiroInformado = fechamentos.reduce((sum, f) => sum + f.saldo_informado_dinheiro, 0);
  const totalQuebraDinheiro = saldoDinheiroEsperado - saldoDinheiroInformado;

  // Consolidação de movimentações por Espécie Financeira entre todos os caixas da unidade
  const especies: ("Dinheiro" | "PIX" | "Cartão Débito" | "Cartão Crédito" | "Frotistas/Prazo")[] = [
    "Dinheiro", "PIX", "Cartão Débito", "Cartão Crédito", "Frotistas/Prazo"
  ];

  const speciesConsolidated = especies.map((esp) => {
    let esperado = 0;
    let informado = 0;
    fechamentos.forEach((f) => {
      const item = f.movimentacoes.find((m) => m.especie === esp);
      if (item) {
        esperado += item.valor_esperado;
        informado += item.valor_informado;
      }
    });
    const diferenca = esperado - informado;
    return {
      especie: esp,
      esperado,
      informado,
      diferenca,
      percentual: esperado > 0 ? (diferenca / esperado) * 100 : 0
    };
  });

  // Contagem de alertas para os turnos
  const caixasNaoConsolidados = fechamentos.filter((f) => f.status !== "consolidado").length;
  const caixasComQuebraCritica = fechamentos.filter(
    (f) => (f.saldo_esperado_dinheiro - f.saldo_informado_dinheiro) > 10.00
  ).length;

  // Proporção atual de despesas de caixa vs faturamento bruto
  const proporcaoDespesasAtual = faturamentoTotal > 0 ? (despesasOperacionais / faturamentoTotal) * 100 : 0;
  const limiteHistorico = activeUnitData.meta.media_historica_despesas_percentual;
  const isRatioAnomalous = proporcaoDespesasAtual > limiteHistorico;

  // Comparação cruzada com as outras unidades para o Painel de Insights
  const allUnitsStats = Object.keys(SIMULATED_DATA).map((unit) => {
    const data = SIMULATED_DATA[unit];
    const unitFat = data.fechamentos.reduce((sum, f) => sum + f.faturamento_bruto, 0);
    const unitDesp = data.despesas.reduce((sum, d) => sum + d.valor, 0);
    return {
      unidade: unit,
      faturamento: unitFat,
      despesas: unitDesp,
      proporcao: unitFat > 0 ? (unitDesp / unitFat) * 100 : 0
    };
  });

  const mediaDespesasOutras = allUnitsStats
    .filter((u) => u.unidade !== selectedUnidade)
    .reduce((sum, u) => sum + u.despesas, 0) / (allUnitsStats.length - 1);

  const percentualExcessoDespesas = mediaDespesasOutras > 0
    ? ((despesasOperacionais - mediaDespesasOutras) / mediaDespesasOutras) * 100
    : 0;

  // Estilos baseados no hostTheme do Cursor (Dark Mode First)
  const styles = {
    container: {
      padding: "20px",
      background: hostTheme.bg.editor,
      color: hostTheme.text.primary,
      fontFamily: "var(--font-family, sans-serif)",
      minHeight: "100vh"
    },
    header: {
      borderBottom: `1px solid ${hostTheme.stroke.primary}`,
      paddingBottom: "16px",
      marginBottom: "24px"
    },
    badgeOrange: {
      background: "rgba(245, 158, 11, 0.15)",
      color: "#f59e0b",
      border: "1px solid rgba(245, 158, 11, 0.3)",
      padding: "2px 8px",
      borderRadius: "4px",
      fontSize: "0.75rem",
      fontWeight: "semibold" as const
    },
    badgeRed: {
      background: "rgba(239, 68, 68, 0.15)",
      color: "#ef4444",
      border: "1px solid rgba(239, 68, 68, 0.3)",
      padding: "2px 8px",
      borderRadius: "4px",
      fontSize: "0.75rem",
      fontWeight: "semibold" as const
    },
    badgeGreen: {
      background: "rgba(16, 185, 129, 0.15)",
      color: "#10b981",
      border: "1px solid rgba(16, 185, 129, 0.3)",
      padding: "2px 8px",
      borderRadius: "4px",
      fontSize: "0.75rem",
      fontWeight: "semibold" as const
    },
    sidebar: {
      background: hostTheme.bg.elevated,
      borderLeft: `1px solid ${hostTheme.stroke.primary}`,
      padding: "20px",
      borderRadius: "0 8px 8px 0"
    },
    dangerRow: {
      background: "rgba(239, 68, 68, 0.08)",
      color: "#fca5a5"
    },
    highlightRow: {
      cursor: "pointer",
      transition: "background 0.2s"
    }
  };

  // Formato monetário brasileiro
  const formatBRL = (v: number) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL"
    }).format(v);
  };

  return (
    <div style={styles.container}>
      {/* HEADER PRINCIPAL */}
      <div style={styles.header}>
        <Row justify="space-between" align="center" wrap gap={16}>
          <Stack gap={4}>
            <H1 style={{ color: hostTheme.text.primary, fontSize: "1.5rem", fontWeight: "bold" }}>
              LOGOS Auditoria de Pista
            </H1>
            <Text tone="secondary" size="small">
              Validação estoica de fechamentos de caixas e identificação nominal de vazamentos
            </Text>
          </Stack>

          <Row gap={12} align="center">
            {/* Seletor de Unidade */}
            <Select
              value={selectedUnidade}
              onChange={(val) => {
                setSelectedUnidade(val);
                setSelectedCaixaId(null); // Reseta drill down
              }}
              options={[
                { value: "Real", label: "Posto Real" },
                { value: "Casa Caiada", label: "Posto Casa Caiada" },
                { value: "VIP", label: "Posto VIP" }
              ]}
              style={{ width: "160px" }}
            />

            {/* Filtro de Data */}
            <Select
              value={selectedDate}
              onChange={setSelectedDate}
              options={[
                { value: "2026-07-03", label: "Hoje (03/07/2026)" },
                { value: "2026-07-02", label: "Ontem (02/07/2026)" },
                { value: "2026-07-01", label: "01/07/2026" }
              ]}
              style={{ width: "180px" }}
            />
          </Row>
        </Row>
      </div>

      <Grid columns="3fr 1fr" gap={20}>
        {/* CORPO DO DASHBOARD */}
        <Stack gap={20}>
          {/* CARDS DE RESUMO FINANCEIRO (KPIs) */}
          <Grid columns={4} gap={12}>
            <Card variant="secondary">
              <CardBody style={{ padding: "16px" }}>
                <Stat
                  value={formatBRL(faturamentoTotal)}
                  label="Faturamento Bruto Total"
                />
                <Text tone="tertiary" size="small" style={{ marginTop: "4px" }}>
                  Soma de todas as vendas brutas registradas
                </Text>
              </CardBody>
            </Card>

            <Card variant="secondary">
              <CardBody style={{ padding: "16px" }}>
                <Stat
                  value={formatBRL(despesasOperacionais)}
                  label="Despesas de Caixa"
                  tone={despesasOperacionais > (faturamentoTotal * 0.05) ? "warning" : undefined}
                />
                <Text tone="tertiary" size="small" style={{ marginTop: "4px" }}>
                  Retiradas da pista/conveniência no dia
                </Text>
              </CardBody>
            </Card>

            <Card variant="secondary">
              <CardBody style={{ padding: "16px" }}>
                <Stat
                  value={formatBRL(saldoDinheiroInformado)}
                  label="Saldo Físico em Espécie"
                  tone="success"
                />
                <Text tone="tertiary" size="small" style={{ marginTop: "4px" }}>
                  Dinheiro físico informado nos cofres/caixas
                </Text>
              </CardBody>
            </Card>

            <Card variant="secondary">
              <CardBody style={{ padding: "16px" }}>
                <Stat
                  value={formatBRL(totalQuebraDinheiro)}
                  label="Quebra de Caixa"
                  tone={totalQuebraDinheiro > 10 ? "danger" : totalQuebraDinheiro > 0 ? "warning" : undefined}
                />
                <Text tone="tertiary" size="small" style={{ marginTop: "4px" }}>
                  Sistêmico vs. Informado pelo Operador
                </Text>
              </CardBody>
            </Card>
          </Grid>

          {/* TABELA DE MOVIMENTAÇÃO POR ESPÉCIE */}
          <Card>
            <CardHeader trailing={
              <Text tone="secondary" size="small">Valores Consolidados</Text>
            }>
              <H3>Movimentação Consolidada por Espécie Financeira</H3>
            </CardHeader>
            <CardBody style={{ padding: "0px" }}>
              <Table
                headers={["Espécie / Modalidade", "Valor Sistêmico (Esperado)", "Valor Informado", "Quebra / Diferença", "Variação %"]}
                rows={speciesConsolidated.map((s) => [
                  <Text weight="medium">{s.especie}</Text>,
                  formatBRL(s.esperado),
                  formatBRL(s.informado),
                  <Text tone={s.diferenca > 10 ? "danger" : s.diferenca > 0 ? "warning" : "primary"}>
                    {formatBRL(s.diferenca)}
                  </Text>,
                  <Text tone={s.percentual > 1 ? "danger" : s.percentual > 0 ? "warning" : "secondary"}>
                    {s.percentual.toFixed(2)}%
                  </Text>
                ])}
                striped
                framed={false}
              />
            </CardBody>
          </Card>

          {/* MÓDULO DE FECHAMENTO DE TURNO */}
          <Card>
            <CardHeader trailing={
              <Row gap={8}>
                {caixasNaoConsolidados > 0 && (
                  <span style={styles.badgeOrange}>{caixasNaoConsolidados} pendentes</span>
                )}
                {caixasComQuebraCritica > 0 && (
                  <span style={styles.badgeRed}>{caixasComQuebraCritica} quebras críticas</span>
                )}
              </Row>
            }>
              <H3>Módulo de Fechamentos de Caixa (Turnos do Dia)</H3>
            </CardHeader>
            <CardBody style={{ padding: "0px" }}>
              <Table
                headers={["ID Caixa", "Tipo", "Operador", "Abertura / Fechamento", "Fat. Bruto", "Dinheiro Esperado", "Dinheiro Informado", "Quebra", "Status"]}
                rows={fechamentos.map((f) => {
                  const quebra = f.saldo_esperado_dinheiro - f.saldo_informado_dinheiro;
                  const isSelected = selectedCaixaId === f.id;
                  
                  return [
                    <Button
                      variant={isSelected ? "primary" : "secondary"}
                      onClick={() => setSelectedCaixaId(isSelected ? null : f.id)}
                      style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                    >
                      {f.id}
                    </Button>,
                    <Text weight="medium" style={{ textTransform: "capitalize" }}>{f.caixa_tipo}</Text>,
                    f.operador_fechamento,
                    `${f.horario_abertura} - ${f.horario_fechamento}`,
                    formatBRL(f.faturamento_bruto),
                    formatBRL(f.saldo_esperado_dinheiro),
                    formatBRL(f.saldo_informado_dinheiro),
                    <Text tone={quebra > 10 ? "danger" : quebra > 0 ? "warning" : "primary"}>
                      {formatBRL(quebra)}
                    </Text>,
                    f.status === "consolidado" ? (
                      <span style={styles.badgeGreen}>Consolidado</span>
                    ) : quebra > 10 ? (
                      <span style={styles.badgeRed}>Quebra Crítica</span>
                    ) : (
                      <span style={styles.badgeOrange}>Pendente</span>
                    )
                  ];
                })}
                striped
                framed={false}
              />
            </CardBody>
          </Card>

          {/* TABELA DE AUDITORIA DE DESPESAS */}
          <Card>
            <CardHeader trailing={
              <Row gap={12} align="center">
                <Text tone="secondary" size="small">Filtrar alertas</Text>
                <Button 
                  variant={onlyAlerts ? "primary" : "secondary"}
                  onClick={() => setOnlyAlerts(!onlyAlerts)}
                  style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                >
                  {onlyAlerts ? "Exibindo Apenas Alertas" : "Exibir Todos"}
                </Button>
                {selectedCaixaId && (
                  <Button
                    variant="ghost"
                    onClick={() => setSelectedCaixaId(null)}
                    style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                  >
                    Limpar Filtro Caixa
                  </Button>
                )}
              </Row>
            }>
              <H3>Tabela de Auditoria de Despesas da Pista / Conveniência</H3>
            </CardHeader>
            <CardBody style={{ padding: "0px" }}>
              <Table
                headers={["Horário", "Caixa", "Categoria", "Valor", "Operador", "Documento Comprobatório", "Status Justificativa"]}
                rows={filteredDespesas.map((d) => {
                  const semCategoria = !d.categoria;
                  const semAnexo = !d.tem_documento;
                  const isCrit = semCategoria || semAnexo;

                  return [
                    d.horario,
                    <Text style={{ textTransform: "capitalize" }}>{d.caixa_tipo}</Text>,
                    semCategoria ? (
                      <Text tone="danger" weight="bold">NÃO CATEGORIZADA</Text>
                    ) : (
                      d.categoria
                    ),
                    <Text tone={isCrit ? "danger" : "primary"} weight={isCrit ? "bold" : "normal"}>
                      {formatBRL(d.valor)}
                    </Text>,
                    d.operador,
                    semAnexo ? (
                      <Text tone="danger" weight="bold">SEM DOCUMENTO ANEXO</Text>
                    ) : (
                      <Text tone="success">Documento Anexado (PDF/IMG)</Text>
                    ),
                    <Text tone={d.status_justificativa === "pendente" ? "warning" : "primary"}>
                      {d.status_justificativa.toUpperCase().replace("_", " ")}
                    </Text>
                  ];
                })}
                striped
                framed={false}
                emptyMessage="Nenhuma despesa suspeita ou filtrada neste período."
              />
            </CardBody>
          </Card>
        </Stack>

        {/* PAINEL LATERAL: INSIGHTS DO AUDITOR */}
        <Stack gap={16} style={{ height: "100%" }}>
          <Card variant="secondary" style={{ borderColor: hostTheme.accent.primary, height: "100%" }}>
            <CardHeader>
              <H3 style={{ color: hostTheme.accent.primary, fontWeight: "bold" }}>
                Insights do Auditor
              </H3>
            </CardHeader>
            <CardBody>
              <Stack gap={12}>
                <Callout tone="info" title="Análise Proporcional de Despesas">
                  <Text size="small">
                    As despesas operacionais da unidade <strong>{selectedUnidade}</strong> equivalem a{" "}
                    <strong>{proporcaoDespesasAtual.toFixed(2)}%</strong> do faturamento total do dia.
                  </Text>
                  <Spacer />
                  <Text size="small">
                    Limite histórico de referência: <strong>{limiteHistorico.toFixed(2)}%</strong>.
                  </Text>
                </Callout>

                {isRatioAnomalous ? (
                  <Callout tone="danger" title="Vazamento Suspeito Detectado!">
                    <Text size="small">
                      A proporção de despesas operacionais em relação ao faturamento está{" "}
                      <strong>{(proporcaoDespesasAtual - limiteHistorico).toFixed(2)}%</strong> acima da média histórica padrão de 5%.
                    </Text>
                  </Callout>
                ) : (
                  <Callout tone="success" title="Despesas Dentro do Padrão">
                    <Text size="small">
                      Índice de despesas operacionais de {proporcaoDespesasAtual.toFixed(2)}% está saudável e de acordo com o limite de 5%.
                    </Text>
                  </Callout>
                )}

                {/* Comparativo de Outliers */}
                {selectedUnidade === "VIP" && (
                  <Callout tone="danger" title="Alerta de Inconsistência Crítica (Outlier)">
                    <Text size="small">
                      A unidade <strong>VIP</strong> teve <strong>{percentualExcessoDespesas.toFixed(1)}%</strong> a mais de despesas de caixa do que a média das outras unidades da rede. Requer auditoria rígida!
                    </Text>
                  </Callout>
                )}

                <Divider />

                <H3 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: hostTheme.text.secondary }}>
                  CONFORMIDADE TÉCNICA (Pydantic)
                </H3>

                <Stack gap={8}>
                  <Row justify="space-between">
                    <Text size="small">Despesas Sem Categoria:</Text>
                    <Text size="small" weight="bold" tone={despesas.filter((d) => !d.categoria).length > 0 ? "danger" : "primary"}>
                      {despesas.filter((d) => !d.categoria).length}
                    </Text>
                  </Row>

                  <Row justify="space-between">
                    <Text size="small">Despesas Sem Documento:</Text>
                    <Text size="small" weight="bold" tone={despesas.filter((d) => !d.tem_documento).length > 0 ? "danger" : "primary"}>
                      {despesas.filter((d) => !d.tem_documento).length}
                    </Text>
                  </Row>

                  <Row justify="space-between">
                    <Text size="small">Turnos c/ Quebra Crítica (&gt;R$10):</Text>
                    <Text size="small" weight="bold" tone={caixasComQuebraCritica > 0 ? "danger" : "primary"}>
                      {caixasComQuebraCritica}
                    </Text>
                  </Row>
                </Stack>

                <Divider />

                <Text tone="tertiary" size="small" italic>
                  Regra de Auditoria Estoica: O capital não fiscalizado tende a dissipar-se. Registros incompletos são considerados vazamentos potenciais até prova documental idônea.
                </Text>
              </Stack>
            </CardBody>
          </Card>
        </Stack>
      </Grid>
    </div>
  );
}