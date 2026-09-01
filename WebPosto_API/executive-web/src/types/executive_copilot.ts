export const COPILOT_ALL_UNITS_LABEL = "Todas as Unidades";

export const COPILOT_PUBLIC_UNITS = [
  { publicName: "AP Casa Caiada", code: 5555 },
  { publicName: "Posto VIP", code: 11495 },
  { publicName: "Posto Real/Doze", code: 74014 },
  { publicName: "Conveniência 24 Horas", code: 118508 },
] as const;

export type CopilotPublicUnitName = (typeof COPILOT_PUBLIC_UNITS)[number]["publicName"];

export type CopilotUnitSelection =
  | { kind: "all"; publicName: typeof COPILOT_ALL_UNITS_LABEL }
  | { kind: "unit"; publicName: CopilotPublicUnitName; code: number };

export const BLOCKED_COMPARISON = "COMPARISON_REQUIRES_MULTIPLE_UNITS";
export const BLOCKED_UNIT_SOURCE = "UNIT_SOURCE_NOT_APPLICABLE";

export const COMPARISON_BLOCKED_COPY =
  "Selecione pelo menos duas unidades compatíveis (por exemplo AP Casa Caiada e Posto VIP) ou Todas as Unidades para comparar.";

export const APPROVED_LOCAL_BADGE = "Aprovado no LOGOS (Sem gravação no ERP)";

export const APPROVER_ROLES = ["director", "admin", "owner"] as const;
export type CopilotApproverRole = (typeof APPROVER_ROLES)[number];
export type CopilotUserRole = CopilotApproverRole | "manager" | string;

export type ExpenseDraftStatus =
  | "DRAFT"
  | "CONFIRMED"
  | "PENDING_APPROVAL"
  | "APPROVED_LOCAL"
  | "REJECTED"
  | "CANCELLED"
  | "EXECUTION_BLOCKED";

export interface ExpenseDraftPayload {
  pergunta?: string;
  unidades?: number[];
  unitPublicName?: string;
  valor?: number | null;
  descricao?: string | null;
}

export interface ExpenseDraftBlocked {
  code: string;
  message: string;
}

export interface ExpenseDraftResponse {
  ok?: boolean;
  draftId?: string;
  actionType: string;
  status: ExpenseDraftStatus | string;
  unitPublicName?: string | null;
  filledFields?: Record<string, unknown> | Array<{ key: string; label?: string; value?: unknown; status?: string }>;
  missingFields?: string[] | Array<{ key: string; label?: string; reason?: string }>;
  autoClassifiedFields?: Array<Record<string, unknown>>;
  valor?: number | null;
  descricao?: string | null;
  requiresConfirmation?: boolean;
  requiresApproval?: boolean;
  riskAssessment?: string | null;
  webpostoWrites: number;
  canExecute: false;
  executionDisabledReason?: string;
  executionCode?: string;
  created?: boolean;
  duplicate?: boolean;
  blocked?: ExpenseDraftBlocked;
  code?: string;
  message?: string;
  permittedActions?: string[];
}

export interface CopilotIdentity {
  role: string | null;
  email?: string | null;
  sub?: string | null;
}
