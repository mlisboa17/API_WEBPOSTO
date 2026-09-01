import type {
  CopilotAnswer,
  ActionDraftProposal,
  ActionFieldItem,
  ActionMissingFieldItem,
  ClaimStatus,
  SpecialistId,
} from "../types/copilot";

/**
 * Função pura que converte e valida o payload HTTP/API recebido do backend
 * para o formato interno CopilotAnswer utilizado pela interface de usuário.
 * 
 * Valida estritamente os tipos dos campos mandatórios sem inventar defaults.
 * Aceita strings vazias válidas (ex: fact="") permitidas no contrato Python.
 */
export function normalizeCopilotAnswer(rawPayload: any): CopilotAnswer {
  if (!rawPayload || typeof rawPayload !== "object") {
    throw new Error("Payload do Copiloto inválido: esperava um objeto JSON.");
  }

  // Se o payload vier envelopado em { success: true, data: { ... } } ou { answer: { ... } }
  const data = rawPayload.data || rawPayload.answerPayload || rawPayload;

  // Validação estrita de existência e tipo dos campos obrigatórios ("" é string válida)
  if (data.answer === undefined || data.answer === null || typeof data.answer !== "string") {
    throw new Error("Payload do Copiloto inválido: campo 'answer' ausente ou inválido.");
  }
  if (data.fact === undefined || data.fact === null || typeof data.fact !== "string") {
    throw new Error("Payload do Copiloto inválido: campo 'fact' ausente ou inválido.");
  }

  const specialist: SpecialistId = (data.specialist as SpecialistId) || "PRESIDENTE";
  const webpostoWrites = typeof data.webpostoWrites === "number" ? data.webpostoWrites : 0;
  const consolidatedScope = Boolean(data.consolidatedScope);

  // Mapeamento de suggestedAction para actionDraft
  const rawSuggestedAction = data.suggestedAction;
  let actionDraft: ActionDraftProposal | null = null;

  if (rawSuggestedAction && typeof rawSuggestedAction === "object") {
    const rawType =
      rawSuggestedAction.actionType ||
      rawSuggestedAction.type ||
      rawSuggestedAction.codigoAcao;

    // Só constrói card actionDraft se houver um actionType explícito de ação
    if (rawType && typeof rawType === "string") {
      const actionType = rawType;
      const status = rawSuggestedAction.status || "DRAFT";
      const title =
        rawSuggestedAction.title ||
        rawSuggestedAction.titulo ||
        (actionType === "CREATE_PRODUCT_DRAFT"
          ? "Proposta DRAFT de Cadastro de Produto"
          : actionType === "CREATE_EXPENSE_DRAFT"
          ? "Proposta DRAFT de Sangria / Despesa"
          : "Proposta DRAFT de Ação");

      const requiresConfirmation = Boolean(
        rawSuggestedAction.requiresConfirmation ?? rawSuggestedAction.requerConfirmacao ?? true
      );
      const requiresApproval = Boolean(
        rawSuggestedAction.requiresApproval ?? rawSuggestedAction.requerAprovacao ?? false
      );

      const riskAssessment =
        rawSuggestedAction.risco ||
        rawSuggestedAction.riskAssessment ||
        rawSuggestedAction.avaliacaoRisco ||
        "Risco de governança pendente de homologação.";

      const executionCode =
        rawSuggestedAction.executionCode ||
        rawSuggestedAction.executionDisabledReason ||
        rawSuggestedAction.motivoBloqueio ||
        "ACTION_EXECUTION_NOT_ENABLED";

      const executionDisabledReason =
        executionCode === "ACTION_EXECUTION_NOT_ENABLED"
          ? "Execução não habilitada nesta demonstração (webpostoWrites=0)."
          : String(executionCode);

      // Mapeamento dinâmico de camposPreenchidos (Object -> Array)
      const filledFields: ActionFieldItem[] = [];
      const camposPreenchidosObj =
        rawSuggestedAction.camposPreenchidos ||
        rawSuggestedAction.filledFields ||
        rawSuggestedAction.payloadPreenchido ||
        {};

      if (Array.isArray(camposPreenchidosObj)) {
        camposPreenchidosObj.forEach((item: any) => {
          if (item && typeof item === "object") {
            filledFields.push({
              key: String(item.key || item.label || "campo"),
              label: String(item.label || item.key || "Campo"),
              value: item.value ?? null,
              status: item.status || "FILLED",
            });
          }
        });
      } else if (typeof camposPreenchidosObj === "object") {
        Object.entries(camposPreenchidosObj).forEach(([key, val]) => {
          let fieldStatus: "FILLED" | "NOT_INFORMED" | "AUTO_CLASSIFIED" = "FILLED";
          let displayVal: any = val;

          if (val && typeof val === "object" && val !== null && "value" in (val as any)) {
            displayVal = (val as any).value;
            if ((val as any).status) {
              fieldStatus = (val as any).status;
            }
          }

          if (key.includes("sugerid") || String(val).includes("AUTO_CLASSIFIED") || key === "categoria_sugerida") {
            fieldStatus = "AUTO_CLASSIFIED";
          }

          if (key === "empresaCodigo" || key === "empresa_codigo") {
            return;
          }

          const labelMap: Record<string, string> = {
            descricao: "Descrição",
            unidade: "Unidade",
            unitPublicName: "Unidade",
            valor: "Valor",
            ean: "EAN / Código de Barras",
            preco: "Preço de Venda",
            categoria: "Categoria",
            categoria_sugerida: "Categoria Sugerida",
            ncm: "NCM",
            custo: "Custo de Aquisição",
            tributacao: "Tributação (ICMS/PIS)",
          };

          if (key === "unidade" || key === "unitPublicName") {
            const code = Number(displayVal);
            if (Number.isFinite(code) && code > 0) {
              const names: Record<number, string> = {
                5555: "AP Casa Caiada",
                11495: "Posto VIP",
                74014: "Posto Real/Doze",
                118508: "Conveniência 24 Horas",
                6666: "Posto VIP",
              };
              displayVal = names[code] || rawSuggestedAction.unitPublicName || displayVal;
            }
          }

          filledFields.push({
            key: key === "unidade" ? "unitPublicName" : key,
            label: labelMap[key] || key.charAt(0).toUpperCase() + key.slice(1),
            value: displayVal ?? null,
            status: fieldStatus,
          });
        });
      }

      // Mapeamento dinâmico de camposObrigatoriosAusentes (Array/Object -> Array)
      const missingFields: ActionMissingFieldItem[] = [];
      const camposAusentesRaw =
        rawSuggestedAction.camposObrigatoriosAusentes ||
        rawSuggestedAction.missingFields ||
        rawSuggestedAction.camposAusentes ||
        [];

      if (Array.isArray(camposAusentesRaw)) {
        camposAusentesRaw.forEach((item: any) => {
          if (typeof item === "string") {
            missingFields.push({
              key: item,
              label: item.charAt(0).toUpperCase() + item.slice(1),
              reason: "Não informado na solicitação",
            });
          } else if (item && typeof item === "object" && item !== null) {
            missingFields.push({
              key: String(item.key || item.label || "campo_ausente"),
              label: String(item.label || item.key || "Campo Pendente"),
              reason: item.reason || item.motivo || "Não informado",
            });
          }
        });
      } else if (typeof camposAusentesRaw === "object" && camposAusentesRaw !== null) {
        Object.entries(camposAusentesRaw).forEach(([key, reason]) => {
          missingFields.push({
            key,
            label: key.charAt(0).toUpperCase() + key.slice(1),
            reason: typeof reason === "string" ? reason : "Não informado",
          });
        });
      }

      actionDraft = {
        actionType,
        status,
        title,
        draftId: rawSuggestedAction.draftId || undefined,
        persisted: Boolean(rawSuggestedAction.persisted || rawSuggestedAction.draftId),
        unitPublicName: rawSuggestedAction.unitPublicName || null,
        valor: typeof rawSuggestedAction.valor === "number" ? rawSuggestedAction.valor : null,
        descricao: typeof rawSuggestedAction.descricao === "string" ? rawSuggestedAction.descricao : null,
        requiresConfirmation,
        requiresApproval,
        filledFields,
        missingFields,
        riskAssessment,
        canExecute: false, // Forçado por regra webpostoWrites=0
        executionDisabledReason,
      };
    }
  }

  // Preservar dados sem inventar defaults
  const inference = typeof data.inference === "string" ? data.inference : "";
  const recommendation = typeof data.recommendation === "string" ? data.recommendation : "";
  const units = Array.isArray(data.units) ? data.units : [];
  const unitPublicNames = Array.isArray(data.unitPublicNames)
    ? data.unitPublicNames.filter((name: unknown) => typeof name === "string" && name !== "6666")
    : [];
  const departments = Array.isArray(data.departments) ? data.departments : [];
  const evidence = Array.isArray(data.evidence) ? data.evidence : [];
  const lineage = Array.isArray(data.lineage) ? data.lineage : [];

  let impact = {
    amount: data.impact?.amount ?? null,
    currency: data.impact?.currency || "BRL",
    status: (data.impact?.status as ClaimStatus) || (data.blocked ? "BLOCKED" : "UNAVAILABLE"),
  };

  let confidence = data.confidence
    ? {
        score: typeof data.confidence.score === "number" ? data.confidence.score : 0,
        level: data.confidence.level || "MEDIA",
        reasons: Array.isArray(data.confidence.reasons) ? data.confidence.reasons : [],
      }
    : {
        score: 0,
        level: "MEDIA" as const,
        reasons: [],
      };

  return {
    specialist,
    answer: data.answer,
    fact: data.fact,
    inference,
    recommendation,
    impact,
    units,
    unitPublicNames,
    departments,
    evidence,
    lineage,
    confidence,
    simulation: data.simulation || null,
    suggestedAction: rawSuggestedAction || null, // Preservado integralmente para auditoria
    actionDraft,
    blocked: data.blocked || null,
    webpostoWrites,
    consolidatedScope,
  };
}
