"use client";

import React, { useState } from "react";
import {
  Database,
  Calendar,
  Clock,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Lock,
  ArrowRight,
  Info,
} from "lucide-react";
import { DataRequestResponse } from "@/types/data-request-types";
import { planDataRequest, confirmDataRequest } from "@/services/data-request-adapter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface DataRequestPanelProps {
  unidades: number[];
  startDate: string;
  endDate: string;
  onPlanCreated: (plan: DataRequestResponse) => void;
  onConfirmSuccess: (confirmed: DataRequestResponse) => void;
  onError: (errorMsg: string, status?: number) => void;
}

export function DataRequestPanel({
  unidades,
  startDate,
  endDate,
  onPlanCreated,
  onConfirmSuccess,
  onError,
}: DataRequestPanelProps) {
  const [isPlanning, setIsPlanning] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<DataRequestResponse | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  const formatDate = (dStr: string) => {
    if (!dStr || !dStr.includes("-")) return dStr;
    const parts = dStr.split("-");
    return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : dStr;
  };

  const handleCreatePlan = async () => {
    if (isPlanning) return;
    setIsPlanning(true);
    setCurrentPlan(null);

    try {
      const plan = await planDataRequest(unidades, startDate, endDate);
      setCurrentPlan(plan);
      onPlanCreated(plan);
    } catch (err: any) {
      onError(err?.message || "Erro ao planejar solicitação de dados.", err?.status);
    } finally {
      setIsPlanning(false);
    }
  };

  const handleConfirmPlan = async () => {
    if (!currentPlan || !currentPlan.requestId || !currentPlan.planHash || isConfirming) return;

    setIsConfirming(true);
    try {
      const confirmed = await confirmDataRequest(currentPlan.requestId, currentPlan.planHash);
      onConfirmSuccess(confirmed);
    } catch (err: any) {
      onError(err?.message || "Erro ao confirmar solicitação de dados.", err?.status);
    } finally {
      setIsConfirming(false);
    }
  };

  const isFakeLocal = currentPlan?.executorMode === "FAKE_LOCAL" || true;

  return (
    <Card className="border-amber-500/30 bg-slate-950/90 text-slate-100 shadow-2xl overflow-hidden backdrop-blur-md">
      <CardContent className="p-6 space-y-5">
        {/* Banner de lacuna de dados e explicação */}
        <div className="flex items-start gap-3.5 bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl text-amber-200 text-xs">
          <Database size={22} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="block text-white text-sm font-bold">
              Dados não consolidados localmente no período selecionado
            </strong>
            <p className="text-amber-200/90 leading-relaxed">
              O período de {formatDate(startDate)} a {formatDate(endDate)} possui lacunas no repositório local. Nenhuma ausência é tratada como zero ou valor nulo fictício.
            </p>
          </div>
        </div>

        {/* Botão Inicial "Preparar busca de dados" (Quando plano ainda não foi criado) */}
        {!currentPlan && (
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Lock size={14} className="text-emerald-400" />
              <span>Somente leitura no ERP • webpostoWrites=0</span>
            </div>

            <Button
              size="sm"
              onClick={handleCreatePlan}
              disabled={isPlanning}
              className="bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs px-5 py-2 rounded-xl shadow-lg shadow-amber-600/20 flex items-center gap-2"
            >
              {isPlanning ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Elaborando plano de busca...</span>
                </>
              ) : (
                <>
                  <Database size={14} />
                  <span>Preparar busca de dados</span>
                </>
              )}
            </Button>
          </div>
        )}

        {/* Exibição do Plano Criado (AWAITING_CONFIRMATION) */}
        {currentPlan && currentPlan.status === "AWAITING_CONFIRMATION" && (
          <div className="space-y-4 pt-2 animate-in fade-in duration-300">
            {/* Banner FAKE_LOCAL Obrigatório */}
            {isFakeLocal && (
              <div className="bg-blue-500/10 border border-blue-500/30 p-3.5 rounded-xl text-xs text-blue-200 flex items-start gap-2.5">
                <Info size={18} className="text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="block text-white font-bold mb-0.5">Validação Local do Fluxo:</strong>
                  <span>Teste local do fluxo de atualização. Nenhuma consulta ao ERP foi realizada e nenhum dado foi alterado.</span>
                </div>
              </div>
            )}

            {/* Detalhes do Plano */}
            <div className="bg-slate-900/80 border border-white/10 rounded-xl p-4 space-y-3 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-amber-500/10 text-amber-300 border-amber-500/30 font-bold uppercase">
                    AWAITING_CONFIRMATION
                  </Badge>
                  <span className="text-slate-300 font-bold">Plano de Preparação #{currentPlan.requestId?.slice(0, 8)}</span>
                </div>
                <span className="text-slate-400 font-mono text-[11px]">planHash: {currentPlan.planHash?.slice(0, 12)}...</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1 text-slate-300">
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 font-medium block">Unidades no Escopo</span>
                  <strong className="text-white font-semibold">{currentPlan.units.join(", ")}</strong>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 font-medium block">Pares Ausentes</span>
                  <strong className="text-amber-400 font-semibold">{currentPlan.missingPairs?.length || 0} dias/filial</strong>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 font-medium block">Tempo Estimado</span>
                  <strong className="text-emerald-400 font-semibold">
                    {currentPlan.estimatedSecondsMin ?? 1}s a {currentPlan.estimatedSecondsMax ?? 5}s
                  </strong>
                </div>
              </div>

              {/* Parâmetros de Segurança do Contrato */}
              <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-white/5">
                <span>Endpoint Lógico: <strong className="text-slate-200">{currentPlan.logicalEndpoint || "ABASTECIMENTO"}</strong></span>
                <span>Operação: <strong className="text-slate-200">{currentPlan.operation || "REFRESH_SDS"}</strong></span>
                <span>Escrita ERP: <strong className="text-emerald-400">webpostoWrites={currentPlan.webpostoWrites ?? 0} (Somente Leitura)</strong></span>
              </div>
            </div>

            {/* Mensagem de Instrução e Botão de Confirmação */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <span className="text-xs text-amber-200 font-medium">
                Revise o escopo acima e confirme a preparação dos dados.
              </span>

              <Button
                size="sm"
                onClick={handleConfirmPlan}
                disabled={isConfirming}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-6 py-2.5 rounded-xl shadow-lg shadow-emerald-600/20 flex items-center gap-2 disabled:opacity-50"
              >
                {isConfirming ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Confirmando solicitação...</span>
                  </>
                ) : (
                  <>
                    <span>Confirmar e Iniciar Preparação</span>
                    <ArrowRight size={14} />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
