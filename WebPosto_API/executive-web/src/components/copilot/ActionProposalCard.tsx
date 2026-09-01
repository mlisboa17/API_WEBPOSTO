"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Save,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type { ActionDraftProposal } from "@/types/copilot";
import { APPROVED_LOCAL_BADGE } from "@/types/executive_copilot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  canApproveExpenseProposal,
  canConfirmExpenseProposal,
  canSaveExpenseProposal,
  neverExposeTechnicalCode,
} from "@/components/copilot/expense-draft-ui";

interface ActionProposalCardProps {
  draft: ActionDraftProposal;
  isAllUnits: boolean;
  userRole?: string | null;
  busy?: boolean;
  errorMessage?: string | null;
  onSaveProposal?: () => void;
  onConfirm?: () => void;
  onApproveLocal?: () => void;
}

function fieldDisplay(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "não informado";
  return neverExposeTechnicalCode(value);
}

export function ActionProposalCard({
  draft,
  isAllUnits,
  userRole,
  busy = false,
  errorMessage,
  onSaveProposal,
  onConfirm,
  onApproveLocal,
}: ActionProposalCardProps) {
  const isExpense = draft.actionType === "CREATE_EXPENSE_DRAFT";
  const showSave = isExpense && canSaveExpenseProposal({
    actionType: draft.actionType,
    isAllUnits,
    persisted: draft.persisted,
    draftId: draft.draftId,
    status: draft.status,
  });
  const showConfirm = isExpense && canConfirmExpenseProposal({
    draftId: draft.draftId,
    status: draft.status,
  });
  const showApprove = isExpense && canApproveExpenseProposal({
    draftId: draft.draftId,
    status: draft.status,
    role: userRole,
  });
  const approvedLocal = draft.status === "APPROVED_LOCAL";

  return (
    <div className="bg-slate-950/90 border border-amber-500/30 rounded-xl p-5 space-y-4 shadow-xl" data-testid="action-proposal-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30 font-bold text-[11px] uppercase">
            {draft.persisted || draft.draftId ? `PROPOSTA ${draft.status}` : "PRÉVIA"}
          </Badge>
          {approvedLocal && (
            <Badge
              variant="outline"
              className="bg-emerald-500/15 text-emerald-300 border-emerald-500/40 font-bold text-[10px]"
              data-testid="approved-local-badge"
            >
              {APPROVED_LOCAL_BADGE}
            </Badge>
          )}
          {draft.requiresConfirmation && draft.status === "DRAFT" && (
            <Badge variant="outline" className="bg-amber-500/10 text-amber-300 border-amber-500/20 font-bold text-[10px] uppercase">
              Confirmação Pendente
            </Badge>
          )}
          {draft.requiresApproval && draft.status !== "APPROVED_LOCAL" && (
            <Badge variant="outline" className="bg-purple-500/10 text-purple-300 border-purple-500/20 font-bold text-[10px] uppercase">
              Aprovação Necessária
            </Badge>
          )}
          <h4 className="text-sm font-bold text-white tracking-tight">{draft.title}</h4>
        </div>
        {draft.draftId ? (
          <span className="text-[10px] text-slate-500 font-mono">ID {draft.draftId.slice(0, 8)}</span>
        ) : null}
      </div>

      {draft.unitPublicName ? (
        <p className="text-xs text-slate-300">
          Unidade: <strong className="text-white">{neverExposeTechnicalCode(draft.unitPublicName)}</strong>
        </p>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900/60 p-3.5 rounded-lg border border-emerald-500/20 space-y-2">
          <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 size={14} /> Campos Fornecidos / Informados
          </span>
          <div className="space-y-1.5 text-xs">
            {draft.filledFields.map((field, fIdx) => (
              <div key={fIdx} className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-white/5 gap-2">
                <span className="text-slate-400 font-medium">{field.label}:</span>
                <div className="flex items-center gap-1.5 text-right">
                  {field.status === "AUTO_CLASSIFIED" && (
                    <Badge variant="outline" className="bg-blue-500/20 text-blue-300 border-blue-500/40 text-[9px] uppercase font-bold py-0 px-1">
                      AUTO_CLASSIFIED
                    </Badge>
                  )}
                  <span className={cn("font-semibold", field.value ? "text-white" : "text-slate-500 italic")}>
                    {fieldDisplay(field.value)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900/60 p-3.5 rounded-lg border border-red-500/20 space-y-2">
          <span className="text-xs font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle size={14} /> Campos Não Informados / Pendentes
          </span>
          <div className="space-y-1.5 text-xs">
            {draft.missingFields.map((field, mIdx) => (
              <div key={mIdx} className="bg-slate-950/60 p-2 rounded border border-red-500/30 space-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-red-300 font-bold block">{field.label}</span>
                  <span className="text-[10px] text-slate-500 italic">não informado</span>
                </div>
                {field.reason && <span className="text-slate-400 text-[11px] block">{field.reason}</span>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {draft.riskAssessment && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-200 flex items-start gap-2">
          <ShieldAlert size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <strong className="block text-amber-300 font-bold">Avaliação de Risco de Governança:</strong>
            <span>{draft.riskAssessment}</span>
          </div>
        </div>
      )}

      {errorMessage ? (
        <p className="text-xs text-red-300 font-medium">{errorMessage}</p>
      ) : null}

      {isExpense ? (
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-white/10">
          {showSave ? (
            <Button
              size="sm"
              onClick={onSaveProposal}
              disabled={busy || isAllUnits}
              title={isAllUnits ? "Selecione uma unidade individual para salvar a proposta." : undefined}
              className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
              data-testid="save-expense-proposal"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              Salvar Proposta
            </Button>
          ) : null}

          {isAllUnits && !draft.draftId ? (
            <span className="text-[11px] text-amber-300">
              Selecione uma unidade individual para salvar a proposta. “Todas as Unidades” não gera DRAFT.
            </span>
          ) : null}

          {showConfirm ? (
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={busy}
              className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold flex items-center gap-1.5"
              data-testid="confirm-expense-proposal"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
              Confirmar
            </Button>
          ) : null}

          {showApprove ? (
            <Button
              size="sm"
              onClick={onApproveLocal}
              disabled={busy}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5"
              data-testid="approve-expense-proposal"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
              Aprovar Localmente
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
