export type StatementTab = "overview" | "import";

export interface BankMovement {
  empresaCodigo?: number | string;
  movimentoContaCodigo?: number | string;
  valor: string;
  dataMovimento: string;
  descricao: string;
  tipo?: string;
  tipoDocumentoOrigem?: string;
  contaCodigo?: number | string;
}

export interface BankMovementsResponse {
  success: boolean;
  data?: BankMovement[];
  total?: number;
  page?: number;
  limit?: number;
  resumo?: Record<string, unknown>;
  error?: string | null;
}

export interface ParsedStatementTransaction {
  id: string;
  data: string;
  descricao: string;
  valor: number;
  tipo?: string;
}

export interface OfxImportPayload {
  cdConta: number;
  cdFilial: number;
  dataInicial: string;
  opcaoImportacao: string;
  transacoes: Array<{
    valor: number;
    data: string;
    descricao: string;
    tipo?: string;
  }>;
}

export type ImportFileKind = "ofx" | "csv";
