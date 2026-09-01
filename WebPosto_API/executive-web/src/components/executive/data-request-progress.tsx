"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Ban,
  Clock,
  Info,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import { DataRequestResponse, DataRequestState } from "@/types/data-request-types";
import { getDataRequestStatus, cancelDataRequest } from "@/services/data-request-adapter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface DataRequestProgressProps {
  initialRequest: DataRequestResponse;
  onCompleted?: (finalState: DataRequestResponse) => void;
  onError?: (errorMsg: string, status?: number) => void;
  onReset?: () => void;
}

const TERMINAL_STATES: Set<DataRequestState> = new Set([
  "SUCCESS",
  "PARTIAL",
  "FAILED",
  "CANCELLED",
  "EXPIRED",
]);

const CANCELABLE_STATES: Set<DataRequestState> = new Set([
  "AWAITING_CONFIRMATION",
  "QUEUED",
]);

const POLLING_INTERVAL_MS = 2000; // Mínimo de 2 segundos conforme requisito
const MAX_POLLING_ITERATIONS = 30; // Limite local de segurança (60 segundos total)

export function DataRequestProgress({
  initialRequest,
  onCompleted,
  onError,
  onReset,
}: DataRequestProgressProps) {
  const [requestState, setRequestState] = useState<DataRequestResponse>(initialRequest);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isPollingStopped, setIsPollingStopped] = useState(false);
  const pollCountRef = useRef(0);

  useEffect(() => {
    let timerId: NodeJS.Timeout | null = null;
    const controller = new AbortController();

    const fetchStatus = async () => {
      if (!requestState.requestId) return;

      try {
        pollCountRef.current += 1;
        const updated = await getDataRequestStatus(requestState.requestId, controller.signal);
        setRequestState(updated);

        if (TERMINAL_STATES.has(updated.status)) {
          setIsPollingStopped(true);
          if (onCompleted) onCompleted(updated);
          return;
        }

        if (pollCountRef.current >= MAX_POLLING_ITERATIONS) {
          setIsPollingStopped(true);
          return;
        }

        // Agendar próximo poll
        timerId = setTimeout(fetchStatus, POLLING_INTERVAL_MS);
      } catch (err: any) {
        if (err.name === "AbortError") return;
        setIsPollingStopped(true);
        if (onError) onError(err?.message || "Erro ao consultar status da solicitação.", err?.status);
      }
    };

    // Iniciar polling se não estiver em estado terminal
    if (!TERMINAL_STATES.has(requestState.status) && requestState.requestId) {
      timerId = setTimeout(fetchStatus, POLLING_INTERVAL_MS);
    } else {
      setIsPollingStopped(true);
    }

    return () => {
      controller.abort();
      if (timerId) clearTimeout(timerId);
    };
  }, [requestState.requestId, requestState.status, onCompleted, onError]);

  const handleCancel = async () => {
    if (!requestState.requestId || isCancelling) return;
    setIsCancelling(true);

    try {
      const cancelled = await cancelDataRequest(requestState.requestId);
      setRequestState(cancelled);
      setIsPollingStopped(true);
    } catch (err: any) {
      if (onError) onError(err?.message || "Erro ao cancelar solicitação.", err?.status);
    } finally {
      setIsCancelling(false);
    }
  };

  const getStateMessage = (status: DataRequestState) => {
    switch (status) {
      case "ALREADY_AVAILABLE":
        return "Os dados deste período já estão disponíveis.";
      case "AWAITING_CONFIRMATION":
        return "Revise o escopo e confirme a preparação dos dados.";
      case "QUEUED":
        return "Solicitação na fila.";
      case "RUNNING":
        return "Buscando e processando os dados autorizados.";
      case "VALIDATING":
        return "Validando paginação, identidade e consistência.";
      case "COMMITTING":
        return "Consolidando os dados validados.";
      case "PARTIAL":
        return "A atualização não foi concluída integralmente. Nenhum resultado parcial será apresentado como fato.";
      case "FAILED":
        return "Não foi possível concluir a atualização. Os dados anteriores foram preservados.";
      case "LOCKED":
        return "Já existe uma atualização em andamento para parte deste período.";
      case "EXPIRED":
        return "Este plano expirou. Prepare uma nova solicitação.";
      case "CANCELLED":
        return "Solicitação de preparação cancelada pelo usuário.";
      case "SUCCESS":
        if (requestState.dataChanged === false || requestState.executorMode === "FAKE_LOCAL") {
          return "Fluxo local de atualização validado. Nenhuma consulta ao ERP foi realizada e nenhum dado foi alterado.";
        }
        return "Atualizações de dados concluídas com sucesso.";
      default:
        return "Processando solicitação de dados.";
    }
  };

  const getStatusBadge = (status: DataRequestState) => {
    switch (status) {
      case "SUCCESS":
        return <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30">SUCESSO</Badge>;
      case "RUNNING":
      case "VALIDATING":
      case "COMMITTING":
        return <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">EM EXECUÇÃO</Badge>;
      case "QUEUED":
        return <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30">NA FILA</Badge>;
      case "PARTIAL":
        return <Badge variant="outline" className="bg-orange-500/10 text-orange-400 border-orange-500/30">PARCIAL</Badge>;
      case "FAILED":
        return <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">FALHA</Badge>;
      case "CANCELLED":
        return <Badge variant="outline" className="bg-slate-800 text-slate-400 border-slate-700">CANCELADO</Badge>;
      case "LOCKED":
        return <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">BLOQUEADO</Badge>;
      default:
        return <Badge variant="outline" className="bg-slate-800 text-slate-300 border-slate-700">{status}</Badge>;
    }
  };

  const isTerminal = TERMINAL_STATES.has(requestState.status);
  const isCancelable = CANCELABLE_STATES.has(requestState.status) && !isCancelling;
  const isFakeLocal = requestState.executorMode === "FAKE_LOCAL" || true;

  const pairsTotal = requestState.progress?.pairsTotal || requestState.missingPairs?.length || 1;
  const pairsDone = requestState.progress?.pairsDone || (isTerminal ? pairsTotal : 0);
  const progressPercent = Math.min(100, Math.round((pairsDone / pairsTotal) * 100));

  return (
    <Card className="border-white/10 bg-slate-900/90 text-slate-100 shadow-2xl overflow-hidden backdrop-blur-md">
      <CardContent className="p-6 space-y-5">
        {/* Header do Status */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            {!isTerminal ? (
              <div className="grid size-9 place-items-center rounded-xl bg-blue-500/10 text-blue-400">
                <Loader2 size={18} className="animate-spin" />
              </div>
            ) : requestState.status === "SUCCESS" ? (
              <div className="grid size-9 place-items-center rounded-xl bg-emerald-500/10 text-emerald-400">
                <CheckCircle2 size={18} />
              </div>
            ) : (
              <div className="grid size-9 place-items-center rounded-xl bg-red-500/10 text-red-400">
                <AlertTriangle size={18} />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-white tracking-tight">
                  Status da Solicitação #{requestState.requestId?.slice(0, 8)}
                </h4>
                {getStatusBadge(requestState.status)}
              </div>
              <span className="text-xs text-slate-400">
                Unidades: {requestState.units?.join(", ")} • webpostoWrites={requestState.webpostoWrites ?? 0}
              </span>
            </div>
          </div>

          {/* Botão de Cancelamento */}
          {isCancelable && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleCancel}
              disabled={isCancelling}
              className="bg-red-500/10 hover:bg-red-500/20 text-red-300 border-red-500/30 text-xs flex items-center gap-1.5"
            >
              {isCancelling ? <Loader2 size={13} className="animate-spin" /> : <Ban size={13} />}
              <span>Cancelar Solicitação</span>
            </Button>
          )}

          {isTerminal && onReset && (
            <Button
              size="sm"
              variant="outline"
              onClick={onReset}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 border-white/10 text-xs flex items-center gap-1.5"
            >
              <RotateCcw size={13} />
              <span>Concluir</span>
            </Button>
          )}
        </div>

        {/* Banner de Aviso FAKE_LOCAL */}
        {isFakeLocal && (
          <div className="bg-blue-500/10 border border-blue-500/30 p-3.5 rounded-xl text-xs text-blue-200 flex items-start gap-2.5">
            <Info size={18} className="text-blue-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-white font-bold mb-0.5">Teste Local de Integração:</strong>
              <span>Teste local do fluxo de atualização. Nenhuma consulta ao ERP foi realizada e nenhum dado foi alterado.</span>
            </div>
          </div>
        )}

        {/* Barra de Progresso */}
        {!isTerminal && (
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-slate-300 font-medium">
              <span>Progresso dos pares dia/unidade ({pairsDone} de {pairsTotal})</span>
              <span>{progressPercent}%</span>
            </div>
            <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-white/5">
              <div
                className="bg-gradient-to-r from-blue-600 to-indigo-500 h-full transition-all duration-500 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* Mensagem descritiva do estado */}
        <div className="bg-slate-950/60 border border-white/5 p-4 rounded-xl text-xs text-slate-200 font-medium leading-relaxed">
          {getStateMessage(requestState.status)}
        </div>
      </CardContent>
    </Card>
  );
}
