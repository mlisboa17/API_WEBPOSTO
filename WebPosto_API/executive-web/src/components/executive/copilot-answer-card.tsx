"use client";

import React from "react";
import {
  FileText,
  Lightbulb,
  Target,
  ArrowRight,
  ShieldCheck,
  Coins,
  CheckCircle2,
  Info,
} from "lucide-react";
import { ActionDraftProposal, CopilotAnswer, ClaimStatus } from "@/types/copilot";
import { SPECIALISTS_CONFIG } from "@/services/copilot-specialists";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ActionProposalCard } from "@/components/copilot/ActionProposalCard";
import { BlockedResponseCard } from "@/components/copilot/BlockedResponseCard";
import { displayUnitNames, hideFuelMetrics } from "@/components/copilot/expense-draft-ui";
import { BLOCKED_COMPARISON } from "@/types/executive_copilot";

interface CopilotAnswerCardProps {
  answer: CopilotAnswer;
  onOpenAudit: (answer: CopilotAnswer) => void;
  isAllUnits?: boolean;
  userRole?: string | null;
  draftBusy?: boolean;
  draftError?: string | null;
  onSaveProposal?: () => void;
  onConfirmDraft?: () => void;
  onApproveDraft?: () => void;
}

export function CopilotAnswerCard({
  answer,
  onOpenAudit,
  isAllUnits = false,
  userRole = null,
  draftBusy = false,
  draftError = null,
  onSaveProposal,
  onConfirmDraft,
  onApproveDraft,
}: CopilotAnswerCardProps) {
  const specConfig = SPECIALISTS_CONFIG[answer.specialist] || SPECIALISTS_CONFIG.PRESIDENTE;

  const isBlocked = answer.impact.status === "BLOCKED" || Boolean(answer.blocked);
  const isUnavailable = answer.impact.status === "UNAVAILABLE";
  const isSameFact = Boolean(answer.fact && answer.answer && answer.answer.trim() === answer.fact.trim());
  const blockedCode = answer.blocked?.code;
  const suppressFuelMetrics = hideFuelMetrics(blockedCode);
  const unitLabel = answer.consolidatedScope
    ? "Todas as Unidades"
    : displayUnitNames(answer.unitPublicNames, answer.units);

  const formatCurrency = (val: number | null) => {
    if (val === null || val === undefined) return "Indisponível";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(val);
  };

  const getImpactLabel = (status: ClaimStatus) => {
    switch (status) {
      case "FACT":
        return "Valor factual";
      case "ESTIMATED":
        return "Impacto estimado";
      case "AUTO_CLASSIFIED":
        return "Valor classificado";
      case "UNAVAILABLE":
        return "Valor indisponível";
      case "BLOCKED":
        return "Consulta bloqueada";
      default:
        return "Impacto";
    }
  };

  const getStatusBadge = () => {
    switch (answer.impact.status) {
      case "FACT":
        return <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30">DADO LOCAL COM EVIDÊNCIA</Badge>;
      case "ESTIMATED":
        return <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30">IMPACTO ESTIMADO</Badge>;
      case "AUTO_CLASSIFIED":
        return <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">CLASSIFICAÇÃO AUTOMÁTICA</Badge>;
      case "UNAVAILABLE":
        return <Badge variant="outline" className="bg-slate-800 text-slate-400 border-slate-700">VALOR INDISPONÍVEL</Badge>;
      case "BLOCKED":
        return <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">CONSULTA BLOQUEADA</Badge>;
      default:
        return null;
    }
  };

  return (
    <Card className="border-white/10 bg-slate-900/90 text-slate-100 shadow-xl overflow-hidden backdrop-blur-md">
      {/* Top Header do Card com o Especialista e o Status da Resposta */}
      <CardHeader className="bg-slate-950/80 border-b border-white/5 p-4 flex flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={cn("grid size-9 place-items-center rounded-xl bg-gradient-to-br text-white font-bold text-xs shadow-md", specConfig.avatarColor)}>
            {answer.specialist[0]}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">{specConfig.name}</h3>
              <span className="text-[10px] text-slate-400">• {specConfig.title}</span>
            </div>
            <p className="text-xs text-slate-400">
              Unidades: {unitLabel}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge()}
        </div>
      </CardHeader>

      <CardContent className="p-5 space-y-5">
        {/* RESPOSTA EM DESTAQUE */}
        <div className="text-sm text-slate-200 leading-relaxed font-medium bg-slate-950/40 p-4 rounded-xl border border-white/5">
          {answer.answer}
        </div>

        {/* TRÊS BLOCOS SEPARADOS: FATO, INFERÊNCIA E RECOMENDAÇÃO (SEM DUPLICAÇÃO) */}
        {!isBlocked && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Bloco 1: Fato (Apenas exibido se não for idêntico à resposta) */}
            {!isSameFact && answer.fact && (
              <div className="bg-slate-950/60 p-4 rounded-xl border border-blue-500/20 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-400">
                  <FileText size={15} />
                  DADO LOCAL COM EVIDÊNCIA
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {answer.fact}
                </p>
              </div>
            )}

            {/* Bloco 2: Inferência */}
            {answer.inference && (
              <div className="bg-slate-950/60 p-4 rounded-xl border border-purple-500/20 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-400">
                  <Lightbulb size={15} />
                  INFERÊNCIA & ANÁLISE
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {answer.inference}
                </p>
              </div>
            )}

            {/* Bloco 3: Recomendação */}
            {answer.recommendation && (
              <div className="bg-slate-950/60 p-4 rounded-xl border border-emerald-500/20 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                  <Target size={15} />
                  RECOMENDAÇÃO EXECUTIVA
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {answer.recommendation}
                </p>
              </div>
            )}
          </div>
        )}

        {answer.actionDraft && (
          <ActionProposalCard
            draft={answer.actionDraft as ActionDraftProposal}
            isAllUnits={isAllUnits}
            userRole={userRole}
            busy={draftBusy}
            errorMessage={draftError}
            onSaveProposal={onSaveProposal}
            onConfirm={onConfirmDraft}
            onApproveLocal={onApproveDraft}
          />
        )}

        {isBlocked && (
          <BlockedResponseCard code={answer.blocked?.code} message={answer.blocked?.message} />
        )}

        {/* ALERTA DE RESPOSTA INDISPONÍVEL */}
        {isUnavailable && (
          <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-slate-300 text-sm">
              <Info size={18} className="text-amber-400" />
              Informações Indisponíveis no Período
            </div>
            <p className="text-slate-300 leading-relaxed">
              Os dados necessários para fundamentação desta análise não estão disponíveis no banco de dados local homologado. Não produzimos dados fictícios nem assumimos premissas sem respaldo fiscal.
            </p>
          </div>
        )}

        {!suppressFuelMetrics && blockedCode !== BLOCKED_COMPARISON && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div className="bg-slate-950/80 p-3.5 rounded-xl border border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="grid size-8 place-items-center rounded-lg bg-emerald-500/10 text-emerald-400">
                <Coins size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-slate-400 font-medium">
                  {getImpactLabel(answer.impact.status)}
                </span>
                <strong className={cn("text-sm tracking-tight", isUnavailable || isBlocked ? "text-slate-400" : "text-emerald-400")}>
                  {formatCurrency(answer.impact.amount)}
                </strong>
              </div>
            </div>
            <Badge variant="outline" className="text-[10px] bg-slate-900 border-white/10 text-slate-400">
              {answer.impact.status}
            </Badge>
          </div>

          {/* Card de Confiança */}
          <div className="bg-slate-950/80 p-3.5 rounded-xl border border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="grid size-8 place-items-center rounded-lg bg-blue-500/10 text-blue-400">
                <ShieldCheck size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-slate-400 font-medium">Confiança Algorítmica</span>
                <strong className="text-sm text-white tracking-tight">
                  {Math.round(answer.confidence.score * 100)}% ({answer.confidence.level})
                </strong>
              </div>
            </div>
            <span className="text-[11px] text-slate-400">{answer.evidence.length} Evidências</span>
          </div>
        </div>
        )}
      </CardContent>

      {/* RODAPÉ DO CARD COM AÇÃO "VER EVIDÊNCIAS / APROFUNDAR AUDITORIA" */}
      <CardFooter className="bg-slate-950/80 border-t border-white/5 p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <CheckCircle2 size={14} className="text-emerald-400" />
          <span>webpostoWrites: {answer.webpostoWrites} (Seguro)</span>
        </div>

        <Button
          size="sm"
          onClick={() => onOpenAudit(answer)}
          className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/20"
        >
          <span>Ver Evidências & Aprofundar Auditoria</span>
          <ArrowRight size={14} />
        </Button>
      </CardFooter>
    </Card>
  );
}
