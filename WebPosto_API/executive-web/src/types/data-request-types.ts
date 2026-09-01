export type DataRequestState =
  | "ALREADY_AVAILABLE"
  | "AWAITING_CONFIRMATION"
  | "QUEUED"
  | "RUNNING"
  | "VALIDATING"
  | "COMMITTING"
  | "SUCCESS"
  | "PARTIAL"
  | "FAILED"
  | "CANCELLED"
  | "EXPIRED"
  | "LOCKED";

export interface DataRequestMissingPair {
  unit: number;
  day: string;
}

export interface DataRequestProgress {
  pairsTotal: number;
  pairsDone: number;
  pagesOk: number;
  pagesFailed: number;
}

export interface DataRequestResponse {
  requestId: string | null;
  planHash: string | null;
  status: DataRequestState;
  units: number[];
  requestedPeriod: { inicio: string; fim: string } | null;
  missingPairs: DataRequestMissingPair[];
  estimatedSecondsMin?: number;
  estimatedSecondsMax?: number;
  queueDelaySeconds?: number;
  estimateConfidence?: string;
  confirmationExpiresAt?: string | null;
  requiresConfirmation?: boolean;
  logicalEndpoint?: string;
  operation?: string;
  progress?: DataRequestProgress;
  executorMode?: string;
  externalRequests?: number;
  webpostoWrites?: number;
  dataChanged?: boolean;
  publishesFact?: boolean;
  ok?: boolean;
  code?: string;
  detail?: string;
  blocked?: { code: string; message: string };
}
