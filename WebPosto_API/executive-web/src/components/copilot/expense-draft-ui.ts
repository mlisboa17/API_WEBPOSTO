import {
  APPROVER_ROLES,
  BLOCKED_COMPARISON,
  BLOCKED_UNIT_SOURCE,
  COMPARISON_BLOCKED_COPY,
  COPILOT_ALL_UNITS_LABEL,
  COPILOT_PUBLIC_UNITS,
  type CopilotPublicUnitName,
  type CopilotUnitSelection,
  type ExpenseDraftResponse,
} from "../../types/executive_copilot.ts";
import type { ActionDraftProposal, ActionFieldItem } from "../../types/copilot";

export const FORBIDDEN_PUBLIC_ALIAS = "6666";
export const EXPENSE_ACTION_TYPE = "CREATE_EXPENSE_DRAFT";

const CODE_TO_PUBLIC_NAME: Record<number, CopilotPublicUnitName> = Object.fromEntries(
  COPILOT_PUBLIC_UNITS.map((unit) => [unit.code, unit.publicName])
) as Record<number, CopilotPublicUnitName>;

const PUBLIC_NAME_TO_CODE: Record<string, number> = Object.fromEntries(
  COPILOT_PUBLIC_UNITS.map((unit) => [unit.publicName, unit.code])
);

export function isAllUnitsSelection(selection: CopilotUnitSelection): boolean {
  return selection.kind === "all";
}

export function unitsForAsk(selection: CopilotUnitSelection): number[] {
  return selection.kind === "all" ? [] : [selection.code];
}

export function publicNameForCode(code?: number | null, fallback?: string): string {
  if (code === 6666) return CODE_TO_PUBLIC_NAME[11495];
  if (!code) return fallback || COPILOT_ALL_UNITS_LABEL;
  return CODE_TO_PUBLIC_NAME[code] || fallback || "Unidade";
}

export function codeForPublicName(name?: string | null): number | null {
  if (!name || name === COPILOT_ALL_UNITS_LABEL) return null;
  return PUBLIC_NAME_TO_CODE[name] ?? null;
}

export function displayUnitNames(publicNames?: string[] | null, codes?: number[] | null): string {
  if (publicNames && publicNames.length > 0) {
    return publicNames.filter((name) => name && name !== FORBIDDEN_PUBLIC_ALIAS).join(", ");
  }
  if (!codes || codes.length === 0) return "Não informada";
  return codes.map((code) => publicNameForCode(code)).join(", ");
}

export function neverExposeTechnicalCode(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (text === FORBIDDEN_PUBLIC_ALIAS) return publicNameForCode(11495);
  const asNumber = Number(text);
  if (Number.isFinite(asNumber) && CODE_TO_PUBLIC_NAME[asNumber]) {
    return CODE_TO_PUBLIC_NAME[asNumber];
  }
  return text;
}

export function canSaveExpenseProposal(opts: {
  actionType?: string;
  isAllUnits: boolean;
  persisted?: boolean;
  draftId?: string | null;
  status?: string;
}): boolean {
  if (opts.actionType !== EXPENSE_ACTION_TYPE) return false;
  if (opts.isAllUnits) return false;
  if (opts.draftId || opts.persisted) return false;
  return !opts.status || opts.status === "DRAFT";
}

export function canConfirmExpenseProposal(opts: { draftId?: string | null; status?: string }): boolean {
  return Boolean(opts.draftId) && opts.status === "DRAFT";
}

export function canApproveExpenseProposal(opts: {
  draftId?: string | null;
  status?: string;
  role?: string | null;
}): boolean {
  const role = String(opts.role || "").trim().toLowerCase();
  const approver = (APPROVER_ROLES as readonly string[]).includes(role);
  return (
    Boolean(opts.draftId) &&
    approver &&
    (opts.status === "CONFIRMED" || opts.status === "PENDING_APPROVAL")
  );
}

export function hideFuelMetrics(blockedCode?: string | null): boolean {
  return blockedCode === BLOCKED_UNIT_SOURCE;
}

export function blockedFriendlyMessage(code?: string | null, backendMessage?: string | null): string {
  if (code === BLOCKED_COMPARISON) return COMPARISON_BLOCKED_COPY;
  return backendMessage || "Esta consulta foi bloqueada.";
}

export function extractExpenseFields(draft: ActionDraftProposal | null | undefined): {
  unitPublicName?: string;
  valor?: number;
  descricao?: string;
} {
  if (!draft) return {};
  const fromFields = (key: string) => draft.filledFields.find((field) => field.key === key)?.value;
  const unitPublicName =
    draft.unitPublicName ||
    (typeof fromFields("unitPublicName") === "string" ? String(fromFields("unitPublicName")) : undefined);
  const rawValor = draft.valor ?? fromFields("valor");
  const valor =
    typeof rawValor === "number"
      ? rawValor
      : typeof rawValor === "string" && rawValor.trim()
        ? Number(String(rawValor).replace(/\./g, "").replace(",", "."))
        : undefined;
  const descricao =
    draft.descricao ||
    (fromFields("descricao") != null ? String(fromFields("descricao")) : undefined);
  return {
    unitPublicName,
    valor: Number.isFinite(valor) ? valor : undefined,
    descricao,
  };
}

function asFilledArray(
  filled: ExpenseDraftResponse["filledFields"],
  unitPublicName?: string | null
): ActionFieldItem[] {
  if (Array.isArray(filled)) {
    return filled
      .filter((item) => item && item.key !== "empresaCodigo" && item.key !== "empresa_codigo")
      .map((item) => ({
        key: String(item.key),
        label: String(item.label || item.key),
        value:
          item.key === "unitPublicName" || item.key === "unidade"
            ? neverExposeTechnicalCode(item.value ?? unitPublicName)
            : (item.value as string | number | null | undefined) ?? null,
        status: (item.status as ActionFieldItem["status"]) || "FILLED",
      }));
  }
  if (!filled || typeof filled !== "object") {
    return unitPublicName
      ? [{ key: "unitPublicName", label: "Unidade", value: unitPublicName, status: "FILLED" }]
      : [];
  }
  return Object.entries(filled)
    .filter(([key]) => key !== "empresaCodigo" && key !== "empresa_codigo")
    .map(([key, val]) => {
      let fieldStatus: ActionFieldItem["status"] = "FILLED";
      let displayVal: unknown = val;
      if (val && typeof val === "object" && val !== null && "value" in val) {
        displayVal = (val as { value?: unknown }).value;
        if ((val as { status?: ActionFieldItem["status"] }).status) {
          fieldStatus = (val as { status?: ActionFieldItem["status"] }).status || "FILLED";
        }
      }
      if (key === "unitPublicName" || key === "unidade") {
        displayVal = neverExposeTechnicalCode(displayVal ?? unitPublicName);
      }
      return {
        key,
        label: key === "unitPublicName" ? "Unidade" : key.charAt(0).toUpperCase() + key.slice(1),
        value: (displayVal as string | number | null | undefined) ?? null,
        status: fieldStatus,
      };
    });
}

export function mergeExpenseDraftResponse(
  current: ActionDraftProposal,
  response: ExpenseDraftResponse
): ActionDraftProposal {
  const unitPublicName = response.unitPublicName || current.unitPublicName || null;
  const filledFields =
    response.filledFields != null ? asFilledArray(response.filledFields, unitPublicName) : current.filledFields;
  return {
    ...current,
    actionType: response.actionType || current.actionType,
    status: response.status || current.status,
    title: current.title,
    draftId: response.draftId || current.draftId,
    persisted: Boolean(response.draftId),
    unitPublicName,
    valor: response.valor ?? current.valor ?? null,
    descricao: response.descricao ?? current.descricao ?? null,
    filledFields,
    missingFields: current.missingFields,
    requiresConfirmation: response.requiresConfirmation ?? current.requiresConfirmation,
    requiresApproval: response.requiresApproval ?? current.requiresApproval,
    canExecute: false,
    executionDisabledReason:
      response.executionDisabledReason ||
      response.executionCode ||
      current.executionDisabledReason ||
      "ACTION_EXECUTION_NOT_ENABLED",
  };
}
