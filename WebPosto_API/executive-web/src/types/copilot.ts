export type SpecialistId = "PRESIDENTE" | "FINANCEIRO" | "OPERACIONAL";

export type ClaimStatus = "FACT" | "ESTIMATED" | "AUTO_CLASSIFIED" | "UNAVAILABLE" | "BLOCKED";

export type ConfidenceLevel = "ALTA" | "MEDIA" | "BAIXA";

export type SourceNature = "LOCAL" | "LOCAL_HOMOLOGATED" | "SNAPSHOT" | "CHECKPOINT";

export interface Impact {
  amount: number | null;
  currency: string;
  status: ClaimStatus;
}

export interface Confidence {
  score: number;
  level: ConfidenceLevel;
  reasons: string[];
}

export interface PeriodWindow {
  inicio: string;
  fim: string;
}

export interface EvidenceItem {
  id: string;
  fonte: string;
  resumo: string;
  claimStatus: ClaimStatus;
  periodo?: PeriodWindow | null;
  dataReferencia?: string | null;
  empresaCodigo?: number | null;
  escopoConsolidado?: boolean;
}

export interface LineageItem {
  origem: string;
  fonte: string;
  periodo: PeriodWindow;
  referencia: string;
  naturezaFonte: SourceNature;
  fonteLocal: boolean;
  empresaCodigo?: number | null;
  escopoConsolidado?: boolean;
  sdsCompletoAte?: string | null;
}

export interface BlockedInfo {
  code: string;
  message: string;
}

export interface ActionFieldItem {
  key: string;
  label: string;
  value?: string | number | null;
  status?: "FILLED" | "NOT_INFORMED" | "AUTO_CLASSIFIED";
}

export interface ActionMissingFieldItem {
  key: string;
  label: string;
  reason?: string;
}

export interface ActionDraftProposal {
  actionType: "PRODUTO" | "DESPESA" | "CREATE_EXPENSE_DRAFT" | string;
  status: "DRAFT" | "CONFIRMED" | "APPROVED_LOCAL" | "PENDING" | "BLOCKED" | string;
  title: string;
  draftId?: string;
  persisted?: boolean;
  unitPublicName?: string | null;
  valor?: number | null;
  descricao?: string | null;
  requiresConfirmation?: boolean;
  requiresApproval?: boolean;
  filledFields: ActionFieldItem[];
  missingFields: ActionMissingFieldItem[];
  riskAssessment?: string;
  canExecute: false;
  executionDisabledReason: string;
}

export interface SuggestedAction {
  actionId?: string;
  actionType?: string;
  title?: string;
  priority?: "ALTA" | "MEDIA" | "BAIXA" | string;
  status?: string;
  requiresConfirmation?: boolean;
  requiresApproval?: boolean;
  camposPreenchidos?: Record<string, unknown>;
  camposObrigatoriosAusentes?: string[];
  risco?: string;
  executionCode?: string;
}

export interface CopilotSimulation {
  scenarioName?: string;
  potentialSavings?: number | null;
  targetUnit?: string;
  [key: string]: unknown;
}

export interface CopilotAnswer {
  specialist: SpecialistId;
  answer: string;
  fact: string;
  inference: string;
  recommendation: string;
  impact: Impact;
  units: number[];
  unitPublicNames?: string[];
  departments: string[];
  probableCause?: string | null;
  evidence: EvidenceItem[];
  lineage: LineageItem[];
  confidence: Confidence;
  simulation?: CopilotSimulation | Record<string, unknown> | null;
  suggestedAction?: SuggestedAction | Record<string, unknown> | null;
  actionDraft?: ActionDraftProposal | null;
  blocked?: BlockedInfo | null;
  webpostoWrites: number;
  consolidatedScope: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content?: string;
  sourceQuestion?: string;
  answer?: CopilotAnswer;
  timestamp: Date;
  status?: "loading" | "success" | "error";
  errorMessage?: string;
  specialist?: SpecialistId;
}

export interface SpecialistConfig {
  id: SpecialistId;
  name: string;
  title: string;
  description: string;
  avatarColor: string;
  badgeBg: string;
  suggestedQuestions: string[];
}

export interface ReconciliationItem {
  ean: string;
  descricao: string;
  empresa_codigo: number;
  preco_venda: number;
  preco_custo_atual: number;
  status_reconciliacao: "PENDING" | "RECONCILED" | "UNMATCHED" | string;
  dfe_nfe_numero?: string | null;
  custo_dfe?: number | null;
}

export interface ReconciliationPayload {
  empresa_codigo: number;
  empresa_cnpj: string;
  xml_content: string;
  itens_pendentes: ReconciliationItem[];
}

export interface ReconciliationResult {
  empresa_codigo: number;
  total_processado: number;
  total_reconciliado: number;
  total_pendente: number;
  webposto_writes: number;
  itens_atualizados: ReconciliationItem[];
}

