"use client";

import React from "react";
import { AlertTriangle, Droplets, GitCompare } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  BLOCKED_COMPARISON,
  BLOCKED_UNIT_SOURCE,
} from "@/types/executive_copilot";
import { blockedFriendlyMessage } from "@/components/copilot/expense-draft-ui";

interface BlockedResponseCardProps {
  code?: string | null;
  message?: string | null;
}

export function BlockedResponseCard({ code, message }: BlockedResponseCardProps) {
  const isComparison = code === BLOCKED_COMPARISON;
  const isSource = code === BLOCKED_UNIT_SOURCE;
  const copy = blockedFriendlyMessage(code, message);

  return (
    <div
      className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-xs space-y-2"
      data-testid="copilot-blocked-card"
      data-blocked-code={code || "BLOCKED"}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-bold text-amber-300 text-sm">
          {isComparison ? <GitCompare size={18} /> : isSource ? <Droplets size={18} /> : <AlertTriangle size={18} />}
          {isComparison
            ? "Comparação exige mais de uma unidade"
            : isSource
              ? "Fonte não aplicável a esta unidade"
              : "Consulta bloqueada"}
        </div>
        <Badge variant="outline" className="bg-amber-500/10 text-amber-200 border-amber-500/30 text-[10px]">
          {isComparison || isSource ? "Orientações" : code || "BLOCKED"}
        </Badge>
      </div>
      <p className="text-amber-100/90 leading-relaxed font-medium">{copy}</p>
      {isSource && message && message !== copy ? (
        <p className="text-amber-100/80 leading-relaxed">{message}</p>
      ) : null}
      {isComparison ? (
        <p className="text-amber-200/70">
          Escolha duas ou mais unidades de pista compatíveis. Conveniência 24 Horas não entra em métricas de combustível.
        </p>
      ) : null}
    </div>
  );
}
