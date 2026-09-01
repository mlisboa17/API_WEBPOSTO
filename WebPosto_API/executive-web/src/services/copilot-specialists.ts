import { SpecialistId, SpecialistConfig } from "../types/copilot";

export const LICENSED_UNITS = [5555, 11495, 74014];

export const SPECIALISTS_CONFIG: Record<SpecialistId, SpecialistConfig> = {
  PRESIDENTE: {
    id: "PRESIDENTE",
    name: "Especialista Presidente",
    title: "Estratégia, DRE & Governança Executiva",
    description: "Visão estratégica consolidada, retorno sobre ativo, governança e alocação de capital.",
    avatarColor: "from-blue-600 to-indigo-700",
    badgeBg: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    suggestedQuestions: [
      "Qual a margem consolidada do grupo e principais gargalos de rentabilidade?",
      "Como está o desempenho comparativo entre Casa Caiada, VIP e Real?",
      "Existem riscos de governança ou vazamento de caixa que exigem intervenção imediata?",
    ],
  },
  FINANCEIRO: {
    id: "FINANCEIRO",
    name: "Especialista Financeiro",
    title: "Fluxo de Caixa, Despesas & Conciliação",
    description: "Análise profunda de despesas de pista, vales, conciliação bancária e faturamento por espécie.",
    avatarColor: "from-emerald-600 to-teal-700",
    badgeBg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    suggestedQuestions: [
      "Qual o total de despesas de pista não justificadas na semana?",
      "Como está a conciliação de vales e faltas dos operadores de caixa?",
      "Qual o impacto de taxas de cartão e prazo de recebimento na DRE?",
    ],
  },
  OPERACIONAL: {
    id: "OPERACIONAL",
    name: "Especialista Operações",
    title: "Pista, Caixas & Auditoria de PDV",
    description: "Auditoria de bicos vs. vendas, fechamento de turno, quebra financeira e conformidade da pista.",
    avatarColor: "from-amber-600 to-orange-700",
    badgeBg: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    suggestedQuestions: [
      "Quais caixas apresentaram quebra financeira acima de R$ 10,00 no período?",
      "Qual a diferença entre a leitura física dos bicos e os cupons fiscais emitidos?",
      "Existem desvios recorrentes nas trocas de turno entre pista e conveniência?",
    ],
  },
};
