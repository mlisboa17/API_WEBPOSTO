import type {
  CopilotIdentity,
  ExpenseDraftPayload,
  ExpenseDraftResponse,
} from "../../types/executive_copilot.ts";

const DRAFTS_BASE = "/api/proxy/executive-copilot/action-drafts";

export class ExpenseDraftRequestError extends Error {
  status: number;
  blocked?: { code: string; message: string };

  constructor(message: string, status: number, blocked?: { code: string; message: string }) {
    super(message);
    this.name = "ExpenseDraftRequestError";
    this.status = status;
    this.blocked = blocked;
  }
}

async function parseDraftResponse(response: Response, fallback: string): Promise<ExpenseDraftResponse> {
  const status = response.status;
  const data = (await response.json().catch(() => ({}))) as ExpenseDraftResponse & {
    detail?: string;
  };

  if (!response.ok) {
    let message = fallback;
    if (status === 401) message = "Sua sessão expirou.";
    if (status === 403) message = "Você não possui permissão para esta ação nesta unidade.";
    if (status === 422) {
      message = data.blocked?.message || data.message || "Selecione uma unidade específica para salvar a proposta de despesa.";
    }
    throw new ExpenseDraftRequestError(message, status, data.blocked);
  }

  if (data?.blocked || data?.ok === false) {
    throw new ExpenseDraftRequestError(
      data.blocked?.message || data.message || "Não foi possível concluir a ação da proposta.",
      422,
      data.blocked
    );
  }

  return {
    ...data,
    actionType: data.actionType || "CREATE_EXPENSE_DRAFT",
    canExecute: false,
    webpostoWrites: typeof data.webpostoWrites === "number" ? data.webpostoWrites : 0,
  };
}

export async function saveExpenseDraft(
  payload: ExpenseDraftPayload,
  signal?: AbortSignal
): Promise<ExpenseDraftResponse> {
  const response = await fetch(`${DRAFTS_BASE}/expenses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
    signal,
  });
  return parseDraftResponse(response, "Erro HTTP ao salvar proposta de despesa.");
}

export async function confirmExpenseDraft(
  draftId: string,
  signal?: AbortSignal
): Promise<ExpenseDraftResponse> {
  const response = await fetch(`${DRAFTS_BASE}/${encodeURIComponent(draftId)}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    signal,
  });
  return parseDraftResponse(response, "Erro HTTP ao confirmar proposta.");
}

export async function approveExpenseDraft(
  draftId: string,
  signal?: AbortSignal
): Promise<ExpenseDraftResponse> {
  const response = await fetch(`${DRAFTS_BASE}/${encodeURIComponent(draftId)}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    signal,
  });
  return parseDraftResponse(response, "Erro HTTP ao aprovar proposta localmente.");
}

export async function fetchCopilotIdentity(signal?: AbortSignal): Promise<CopilotIdentity> {
  const response = await fetch("/api/proxy/auth/me?demo=copilot", {
    method: "GET",
    credentials: "include",
    signal,
  });
  if (!response.ok) {
    return { role: null };
  }
  const data = await response.json().catch(() => ({}));
  return {
    role: typeof data.role === "string" ? data.role : null,
    email: data.email ?? null,
    sub: data.sub ?? null,
  };
}
