"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  Send,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  User,
  HelpCircle,
  ArrowUpRight,
  Server,
  LogIn,
  Calendar,
} from "lucide-react";
import { SpecialistId, CopilotAnswer, ChatMessage, ActionDraftProposal } from "@/types/copilot";
import { SPECIALISTS_CONFIG } from "@/services/copilot-specialists";
import {
  queryHttpCopilot,
  fetchCopilotDateCoverage,
  fetchCopilotHealth,
  DateCoverageResponse,
} from "@/services/http-copilot-adapter";
import {
  saveExpenseDraft,
  confirmExpenseDraft,
  approveExpenseDraft,
  fetchCopilotIdentity,
} from "@/services/api/executive_copilot_api";
import { COPILOT_ALL_UNITS_LABEL, BLOCKED_UNIT_SOURCE, type CopilotUnitSelection } from "@/types/executive_copilot";
import {
  extractExpenseFields,
  isAllUnitsSelection,
  mergeExpenseDraftResponse,
  unitsForAsk,
} from "@/components/copilot/expense-draft-ui";
import { UnitSelector } from "@/components/copilot/UnitSelector";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { CopilotAnswerCard } from "@/components/executive/copilot-answer-card";
import { CopilotAuditPanel } from "@/components/executive/copilot-audit-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { DataRequestResponse } from "@/types/data-request-types";
import { DataRequestPanel } from "@/components/executive/data-request-panel";
import { DataRequestProgress } from "@/components/executive/data-request-progress";
import {
  evaluatePeriodCoverage,
  CoverageEvalResult,
} from "@/utils/coverage-evaluator";

// Estados explícitos da Cobertura de Datas
export type CoverageState =
  | { status: "loading" }
  | { status: "available"; data: DateCoverageResponse }
  | { status: "empty"; data: DateCoverageResponse }
  | { status: "source_not_applicable"; message: string }
  | { status: "unauthorized"; message: string }
  | { status: "forbidden"; message: string }
  | { status: "error"; message: string };

const LOGIN_REDIRECT_URL = "/login?next=%2Fexecutive%2Fcopilot";

// Perguntas recomendadas da apresentação
const PRESENTATION_QUESTIONS = [
  "Compare o faturamento entre as unidades.",
  "Qual o ticket médio de cada unidade?",
  "Quantos litros e abastecimentos tivemos?",
  "Podemos afirmar qual foi o lucro?",
];

export default function ExecutiveCopilotPage() {
  const {
    periodDates,
    setCustomDates,
    periodLabel,
  } = useGlobalFilter();

  const [activeSpecialist, setActiveSpecialist] = useState<SpecialistId>("PRESIDENTE");
  const [questionInput, setQuestionInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [lastAttemptedQuery, setLastAttemptedQuery] = useState<string | null>(null);
  const [unitSelection, setUnitSelection] = useState<CopilotUnitSelection>({
    kind: "all",
    publicName: COPILOT_ALL_UNITS_LABEL,
  });
  const [userRole, setUserRole] = useState<string | null>(null);
  const [draftBusyId, setDraftBusyId] = useState<string | null>(null);
  const [draftErrors, setDraftErrors] = useState<Record<string, string>>({});

  // Estado estrito da cobertura de datas, Health Status, DATA-ON-DEMAND e bloqueio por resposta
  const [coverageState, setCoverageState] = useState<CoverageState>({ status: "loading" });
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [activeDataRequest, setActiveDataRequest] = useState<DataRequestResponse | null>(null);
  const [isPeriodBlockedByAnswer, setIsPeriodBlockedByAnswer] = useState(false);

  // Painel de auditoria selecionado
  const [selectedAuditAnswer, setSelectedAuditAnswer] = useState<CopilotAnswer | null>(null);
  const [isAuditPanelOpen, setIsAuditPanelOpen] = useState(false);

  // Prevenção de Race Conditions
  const abortControllerRef = useRef<AbortController | null>(null);
  const dateCoverageControllerRef = useRef<AbortController | null>(null);
  const activeQueryIdRef = useRef<number>(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isAllUnits = isAllUnitsSelection(unitSelection);
  const targetUnits = unitsForAsk(unitSelection);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Redirecionamento limpo para login no caso de HTTP 401
  const handleNavigateToLogin = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (dateCoverageControllerRef.current) {
      dateCoverageControllerRef.current.abort();
    }

    setMessages([]);
    setQuestionInput("");
    setActiveDataRequest(null);
    setErrorMessage(null);
    setErrorStatus(null);

    window.location.href = LOGIN_REDIRECT_URL;
  };

  // Consumo do Health Status no carregamento inicial
  useEffect(() => {
    let isMounted = true;
    fetchCopilotHealth()
      .then((healthy) => {
        if (isMounted) setIsBackendHealthy(healthy);
      })
      .catch(() => {
        if (isMounted) setIsBackendHealthy(false);
      });
    fetchCopilotIdentity()
      .then((identity) => {
        if (isMounted) setUserRole(identity.role);
      })
      .catch(() => {
        if (isMounted) setUserRole(null);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Atualização dinâmica de cobertura de datas ao mudar unidade / consolidado (com AbortController)
  useEffect(() => {
    if (dateCoverageControllerRef.current) {
      dateCoverageControllerRef.current.abort();
    }
    const controller = new AbortController();
    dateCoverageControllerRef.current = controller;

    setCoverageState({ status: "loading" });
    const queryUnits = targetUnits;

    fetchCopilotDateCoverage(queryUnits, controller.signal)
      .then((cov) => {
        if (!controller.signal.aborted) {
          if (cov.blocked?.code === BLOCKED_UNIT_SOURCE) {
            setCoverageState({ status: "source_not_applicable", message: cov.blocked.message });
          } else if (cov.empty || !cov.suggestedStartDate || !cov.suggestedEndDate) {
            setCoverageState({ status: "empty", data: cov });
          } else {
            setCoverageState({ status: "available", data: cov });
          }
        }
      })
      .catch((err: any) => {
        if (controller.signal.aborted) return;
        const status = err?.status || null;
        if (status === 401) {
          setCoverageState({
            status: "unauthorized",
            message: "Sua sessão expirou. Entre novamente para consultar a cobertura.",
          });
        } else if (status === 403) {
          setCoverageState({
            status: "forbidden",
            message: "Você não possui acesso à cobertura desta unidade.",
          });
        } else {
          setCoverageState({
            status: "error",
            message: "Não foi possível consultar a cobertura agora.",
          });
        }
      });

    return () => {
      controller.abort();
    };
  }, [unitSelection]);

  // Quando os filtros globais ou o especialista mudam, cancela consultas em andamento e invalida planos ativos
  useEffect(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    activeQueryIdRef.current += 1;
    setIsLoading(false);
    setActiveDataRequest(null);
    setIsPeriodBlockedByAnswer(false);
  }, [unitSelection, periodDates.start, periodDates.end, activeSpecialist]);

  // Avaliação do estado de cobertura derivada
  const rawCoverage =
    coverageState.status === "available" || coverageState.status === "empty"
      ? coverageState.data
      : null;
  const rawFetchErrorStatus =
    coverageState.status === "unauthorized"
      ? 401
      : coverageState.status === "forbidden"
      ? 403
      : coverageState.status === "error"
      ? 500
      : null;

  const coverageEval: CoverageEvalResult =
    coverageState.status === "source_not_applicable"
      ? {
          status: "NO_COVERAGE",
          isCovered: false,
          canPlanDataRequest: false,
          reason: coverageState.message,
        }
      : evaluatePeriodCoverage(
          rawCoverage,
          periodDates.start,
          periodDates.end,
          rawFetchErrorStatus
        );

  const currentSpecialistConfig = SPECIALISTS_CONFIG[activeSpecialist];

  const handleSendQuestion = async (queryText?: string) => {
    const textToQuery = (queryText || questionInput).trim();
    if (!textToQuery || isLoading) return;

    setErrorMessage(null);
    setErrorStatus(null);
    setLastAttemptedQuery(textToQuery);

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const queryId = ++activeQueryIdRef.current;
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    const newUserMessage: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: textToQuery,
      timestamp: new Date(),
      specialist: activeSpecialist,
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setQuestionInput("");
    setIsLoading(true);

    try {
      const answer = await queryHttpCopilot({
        question: textToQuery,
        specialist: activeSpecialist,
        unidades: targetUnits,
        startDate: periodDates.start,
        endDate: periodDates.end,
        signal: abortController.signal,
      });

      if (queryId !== activeQueryIdRef.current) {
        return;
      }

      // Se a resposta retornar BLOCKED por PERIOD_BLOCKED, ativa o CTA do DataRequestPanel
      if (
        (answer.impact?.status === "BLOCKED" || answer.blocked) &&
        (answer.blocked?.code === "PERIOD_BLOCKED" || (answer as any).blockedCode === "PERIOD_BLOCKED")
      ) {
        setIsPeriodBlockedByAnswer(true);
      }

      const newAssistantMessage: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        answer,
        sourceQuestion: textToQuery,
        timestamp: new Date(),
        status: "success",
        specialist: activeSpecialist,
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
    } catch (err: any) {
      if (err.name === "AbortError" || queryId !== activeQueryIdRef.current) {
        return;
      }

      const status = err?.status || null;
      const errorMsg = err?.message || "Erro de conexão ao consultar o Copiloto Executivo.";
      setErrorMessage(errorMsg);
      setErrorStatus(status);

      const newAssistantErrorMessage: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        timestamp: new Date(),
        status: "error",
        errorMessage: errorMsg,
        specialist: activeSpecialist,
      };
      setMessages((prev) => [...prev, newAssistantErrorMessage]);
    } finally {
      if (queryId === activeQueryIdRef.current) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  };

  const handleRetryQuestion = () => {
    if (lastAttemptedQuery) {
      handleSendQuestion(lastAttemptedQuery);
    }
  };

  const handleClearSession = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    activeQueryIdRef.current += 1;
    setMessages([]);
    setErrorMessage(null);
    setErrorStatus(null);
    setLastAttemptedQuery(null);
    setIsLoading(false);
    setIsPeriodBlockedByAnswer(false);
  };

  const handleOpenAudit = (answer: CopilotAnswer) => {
    setSelectedAuditAnswer(answer);
    setIsAuditPanelOpen(true);
  };

  const patchDraft = (messageId: string, next: ActionDraftProposal) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId && msg.answer
          ? { ...msg, answer: { ...msg.answer, actionDraft: next } }
          : msg
      )
    );
  };

  const runDraftAction = async (
    messageId: string,
    action: () => Promise<ActionDraftProposal>
  ) => {
    setDraftBusyId(messageId);
    setDraftErrors((prev) => ({ ...prev, [messageId]: "" }));
    try {
      const next = await action();
      patchDraft(messageId, next);
    } catch (err: any) {
      setDraftErrors((prev) => ({
        ...prev,
        [messageId]: err?.message || "Não foi possível atualizar a proposta.",
      }));
    } finally {
      setDraftBusyId(null);
    }
  };

  const handleSaveProposal = (message: ChatMessage) => {
    if (!message.answer?.actionDraft || isAllUnits) return;
    const fields = extractExpenseFields(message.answer.actionDraft);
    runDraftAction(message.id, async () => {
      const saved = await saveExpenseDraft({
        pergunta: message.sourceQuestion,
        unidades: targetUnits,
        unitPublicName: unitSelection.kind === "unit" ? unitSelection.publicName : fields.unitPublicName,
        valor: fields.valor,
        descricao: fields.descricao,
      });
      return mergeExpenseDraftResponse(message.answer!.actionDraft!, saved);
    });
  };

  const handleConfirmDraft = (message: ChatMessage) => {
    const draftId = message.answer?.actionDraft?.draftId;
    if (!draftId) return;
    runDraftAction(message.id, async () => {
      const confirmed = await confirmExpenseDraft(draftId);
      return mergeExpenseDraftResponse(message.answer!.actionDraft!, confirmed);
    });
  };

  const handleApproveDraft = (message: ChatMessage) => {
    const draftId = message.answer?.actionDraft?.draftId;
    if (!draftId) return;
    runDraftAction(message.id, async () => {
      const approved = await approveExpenseDraft(draftId);
      return mergeExpenseDraftResponse(message.answer!.actionDraft!, approved);
    });
  };

  const formatDateDisplay = (dateStr: string | null) => {
    if (!dateStr || !dateStr.includes("-")) return dateStr || "";
    const parts = dateStr.split("-");
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return dateStr;
  };

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      {/* BANNER DE COBERTURA DE DATAS E STATUS DO BACKEND */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-900/90 border border-white/10 text-xs shadow-lg backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              "grid size-7 place-items-center rounded-lg text-white shrink-0",
              isBackendHealthy === false ||
                coverageState.status === "unauthorized" ||
                coverageState.status === "forbidden" ||
                coverageState.status === "error"
                ? "bg-red-500/20 text-red-400"
                : "bg-emerald-500/20 text-emerald-400"
            )}
          >
            <Server size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <strong className="text-white font-semibold">Backend Conectado — HTTP Real</strong>
              {isBackendHealthy !== null && (
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[9px] uppercase font-bold",
                    isBackendHealthy
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                      : "bg-red-500/20 text-red-300 border-red-500/40"
                  )}
                >
                  {isBackendHealthy ? "Online" : "Indisponível"}
                </Badge>
              )}
            </div>

            <span className="text-slate-400">
              {coverageState.status === "loading" && "Consultando cobertura de datas do servidor..."}
              {coverageState.status === "available" &&
                (coverageEval.status === "COVERED"
                  ? `Período selecionado totalmente coberto (${formatDateDisplay(coverageState.data.suggestedStartDate)} a ${formatDateDisplay(coverageState.data.suggestedEndDate)})`
                  : coverageEval.status === "OUTSIDE_AVAILABLE_RANGE"
                  ? `Período selecionado (${formatDateDisplay(periodDates.start)} a ${formatDateDisplay(periodDates.end)}) fora da faixa disponível (${formatDateDisplay(coverageState.data.suggestedStartDate)} a ${formatDateDisplay(coverageState.data.suggestedEndDate)})`
                  : coverageEval.status === "INTERSECTS_GAP"
                  ? "O período selecionado intersecta lacunas de dados não consolidados."
                  : `Dados disponíveis de ${formatDateDisplay(coverageState.data.suggestedStartDate)} a ${formatDateDisplay(coverageState.data.suggestedEndDate)}`)}
              {coverageState.status === "empty" && "Sem período consolidado disponível para este escopo."}
              {coverageState.status === "source_not_applicable" && coverageState.message}
              {coverageState.status === "unauthorized" && coverageState.message}
              {coverageState.status === "forbidden" && coverageState.message}
              {coverageState.status === "error" && coverageState.message}
            </span>
          </div>
        </div>

        {coverageState.status === "available" && (
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              setCustomDates(
                coverageState.data.suggestedStartDate!,
                coverageState.data.suggestedEndDate!
              )
            }
            className="h-7 text-[11px] bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border-blue-500/30 flex items-center gap-1 shrink-0 font-medium"
          >
            <Calendar size={12} /> Usar Período Disponível
          </Button>
        )}

        {coverageState.status === "unauthorized" && (
          <Button
            size="sm"
            onClick={handleNavigateToLogin}
            className="h-7 text-[11px] bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1 shrink-0 font-bold shadow-md shadow-blue-600/20"
          >
            <LogIn size={12} /> Entrar novamente
          </Button>
        )}
      </div>

      {/* HEADER DA PÁGINA */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">
              Copiloto Multi-Especialista
            </Badge>
            <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">
              LOGOS Intelligence · HTTP Live
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <Bot className="text-blue-400" size={32} />
            Copiloto Executivo LOGOS
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Consultoria fundamentada para sócios e diretores • {unitSelection.publicName} • {periodLabel}
          </p>
        </div>

        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearSession}
            className="border-white/10 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs flex items-center gap-2 self-start md:self-auto"
          >
            <RefreshCw size={14} />
            Nova Sessão de Auditoria
          </Button>
        )}
      </header>

      {/* FILTROS GLOBAIS (FILIAL + PERÍODO) */}
      <div className="space-y-3">
        <UnitSelector value={unitSelection} onChange={setUnitSelection} />
        <GlobalFilterHeader hideFilial />
      </div>

      {/* PAINEL DATA-ON-DEMAND: QUANDO O PERÍODO SOLICITADO ESTIVER FORA DA COBERTURA OU COM GAPS */}
      {activeDataRequest && activeDataRequest.status !== "AWAITING_CONFIRMATION" ? (
        <DataRequestProgress
          initialRequest={activeDataRequest}
          onReset={() => setActiveDataRequest(null)}
          onError={(msg, status) => {
            setErrorMessage(msg);
            setErrorStatus(status || null);
          }}
        />
      ) : coverageState.status !== "source_not_applicable" &&
        (coverageEval.canPlanDataRequest || isPeriodBlockedByAnswer) ? (
        <DataRequestPanel
          unidades={targetUnits}
          startDate={periodDates.start}
          endDate={periodDates.end}
          onPlanCreated={(plan) => setActiveDataRequest(plan)}
          onConfirmSuccess={(confirmed) => setActiveDataRequest(confirmed)}
          onError={(msg, status) => {
            setErrorMessage(msg);
            setErrorStatus(status || null);
          }}
        />
      ) : null}

      {/* SELEÇÃO DE ESPECIALISTAS */}
      <div className="space-y-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Sparkles size={14} className="text-blue-400" />
          Selecione o Especialista para Consulta
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {(Object.keys(SPECIALISTS_CONFIG) as SpecialistId[]).map((specId) => {
            const spec = SPECIALISTS_CONFIG[specId];
            const isSelected = activeSpecialist === specId;

            return (
              <button
                key={specId}
                type="button"
                onClick={() => setActiveSpecialist(specId)}
                className={cn(
                  "flex flex-col text-left p-4 rounded-xl border transition-all duration-200 relative overflow-hidden group",
                  isSelected
                    ? "bg-slate-900 border-blue-500 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500/50"
                    : "bg-slate-950/70 border-white/10 hover:border-white/20 hover:bg-slate-900/60"
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={cn(
                        "grid size-8 place-items-center rounded-lg bg-gradient-to-br text-white font-bold text-xs shadow-md",
                        spec.avatarColor
                      )}
                    >
                      {specId[0]}
                    </div>
                    <div>
                      <strong className="block text-sm text-white font-bold">{spec.name}</strong>
                      <span className="text-[11px] text-slate-400">{spec.title}</span>
                    </div>
                  </div>
                  {isSelected && (
                    <Badge variant="outline" className={spec.badgeBg}>
                      Ativo
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 mt-1">{spec.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* PERGUNTAS SUGERIDAS */}
      <div className="space-y-2">
        <span className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
          <HelpCircle size={13} className="text-blue-400" />
          Perguntas Recomendadas para Apresentação Executiva:
        </span>
        <div className="flex flex-wrap gap-2">
          {PRESENTATION_QUESTIONS.concat(currentSpecialistConfig.suggestedQuestions).map(
            (sug, sIdx) => (
              <button
                key={sIdx}
                type="button"
                onClick={() => handleSendQuestion(sug)}
                disabled={isLoading}
                className="text-xs bg-slate-900/80 hover:bg-blue-600/20 border border-white/10 hover:border-blue-500/40 text-slate-300 hover:text-blue-200 px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 text-left disabled:opacity-50"
              >
                <span>{sug}</span>
                <ArrowUpRight size={13} className="text-slate-500 shrink-0" />
              </button>
            )
          )}
        </div>
      </div>

      {/* ÁREA PRINCIPAL DA CONVERSA */}
      <div className="space-y-6 min-h-[400px]">
        {/* ESTADO VAZIO */}
        {messages.length === 0 && !isLoading && (
          <Card className="border-white/10 bg-slate-900/60 p-8 text-center space-y-4">
            <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Bot size={36} />
            </div>
            <div className="max-w-md mx-auto space-y-2">
              <h3 className="text-lg font-bold text-white">Inicie uma Consulta Executiva</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Selecione um especialista e digite uma pergunta para consultar o banco de dados via backend local.
              </p>
            </div>
          </Card>
        )}

        {/* HISTÓRICO DE MENSAGENS */}
        {messages.map((msg) => (
          <div key={msg.id} className="space-y-3 animate-in fade-in duration-300">
            {msg.role === "user" ? (
              <div className="flex justify-end">
                <div className="max-w-2xl bg-blue-600 text-white p-4 rounded-2xl rounded-tr-none shadow-lg space-y-1">
                  <div className="flex items-center justify-between gap-4 text-[10px] text-blue-200 font-semibold mb-1">
                    <span className="flex items-center gap-1">
                      <User size={12} /> Direção / Consulta
                    </span>
                    <span>
                      {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <p className="text-sm font-medium leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ) : msg.status === "error" ? (
              <Card className="border-red-500/30 bg-red-500/10 p-5 text-xs text-red-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-bold text-red-400 text-sm">
                    <AlertTriangle size={18} /> Erro ao Processar Consulta
                  </div>
                  <Badge variant="outline" className="bg-red-500/20 text-red-300 border-red-500/40">
                    {errorStatus ? `HTTP ${errorStatus}` : "Erro"}
                  </Badge>
                </div>
                <p className="text-red-200/90 leading-relaxed font-medium">
                  {msg.errorMessage || "Não foi possível processar a consulta."}
                </p>
                <div className="flex items-center gap-2 pt-1">
                  {errorStatus === 401 ? (
                    <Button
                      size="sm"
                      onClick={handleNavigateToLogin}
                      className="bg-blue-600 hover:bg-blue-500 text-white text-xs flex items-center gap-1.5 font-bold"
                    >
                      <LogIn size={13} /> Entrar novamente
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleRetryQuestion}
                      className="border-red-500/40 bg-red-500/20 text-white hover:bg-red-500/30 text-xs flex items-center gap-1.5"
                    >
                      <RefreshCw size={13} /> Tentar Novamente
                    </Button>
                  )}
                </div>
              </Card>
            ) : msg.answer ? (
              <CopilotAnswerCard
                answer={msg.answer}
                onOpenAudit={handleOpenAudit}
                isAllUnits={isAllUnits}
                userRole={userRole}
                draftBusy={draftBusyId === msg.id}
                draftError={draftErrors[msg.id] || null}
                onSaveProposal={() => handleSaveProposal(msg)}
                onConfirmDraft={() => handleConfirmDraft(msg)}
                onApproveDraft={() => handleApproveDraft(msg)}
              />
            ) : null}
          </div>
        ))}

        {/* ESTADO DE CARREGAMENTO */}
        {isLoading && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs text-blue-400 font-semibold animate-pulse">
              <Sparkles size={16} className="animate-spin" />
              <span>O especialista {currentSpecialistConfig.name} está consultando o backend HTTP real...</span>
            </div>
            <Card className="border-white/10 bg-slate-900/80 p-6 space-y-4">
              <Skeleton className="h-5 w-3/4 bg-slate-800" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                <Skeleton className="h-28 bg-slate-800/60 rounded-xl" />
                <Skeleton className="h-28 bg-slate-800/60 rounded-xl" />
                <Skeleton className="h-28 bg-slate-800/60 rounded-xl" />
              </div>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* CAMPO FIXO DE PERGUNTA */}
      <div className="sticky bottom-4 z-20">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendQuestion();
          }}
          className="flex items-center gap-2 p-2 rounded-2xl bg-slate-950/95 border border-white/10 backdrop-blur-md shadow-2xl"
        >
          <div className="grid size-10 place-items-center rounded-xl bg-blue-500/10 text-blue-400 shrink-0 ml-1">
            <Bot size={20} />
          </div>

          <input
            type="text"
            value={questionInput}
            onChange={(e) => setQuestionInput(e.target.value)}
            placeholder={`Pergunte ao ${currentSpecialistConfig.name} sobre ${unitSelection.publicName}...`}
            disabled={isLoading}
            className="flex-1 bg-transparent px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none disabled:opacity-50"
          />

          <Button
            type="submit"
            disabled={isLoading || !questionInput.trim()}
            className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-5 py-2.5 text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/20 shrink-0 disabled:opacity-50"
          >
            <span>Enviar</span>
            <Send size={14} />
          </Button>
        </form>
      </div>

      {/* PAINEL DE AUDITORIA */}
      <CopilotAuditPanel
        answer={selectedAuditAnswer}
        isOpen={isAuditPanelOpen}
        onClose={() => {
          setIsAuditPanelOpen(false);
          setSelectedAuditAnswer(null);
        }}
      />
    </div>
  );
}
