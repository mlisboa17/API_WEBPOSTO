import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8050";

const paymentModes = [
  "Dinheiro",
  "PIX",
  "Cartao Debito",
  "Cartao Credito",
  "Frotistas/Prazo",
] as const;

type UnitName = "Real" | "Casa Caiada" | "VIP";
type RegisterStatus = "Aberto" | "Fechado" | "Consolidado";
type CashKind = "Pista" | "Conveniencia" | "Restaurante";
type PaymentMode = (typeof paymentModes)[number];

type CashRegister = {
  id: string;
  unidade: UnitName;
  data: string;
  caixa: CashKind;
  operador: string;
  status: RegisterStatus;
  vendasBrutas: number;
  despesas: number;
  saldoEspecie: number;
  pagamentos: {
    modalidade: PaymentMode;
    valorSistema: number;
    valorInformado: number;
  }[];
};

type AuditExpense = {
  id: string;
  unidade: UnitName;
  data: string;
  horario: string;
  categoria: string | null;
  valor: number;
  operador: string;
  temAnexo: boolean;
  justificativa: string | null;
};

function todaySaoPaulo() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function toNumber(value: unknown) {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value === "string") {
    const normalized = value.replace(/\./g, "").replace(",", ".");
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function firstNumber(row: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = toNumber(row[key]);
    if (value !== 0) return value;
  }
  return 0;
}

function firstText(row: Record<string, unknown>, keys: string[], fallback = "") {
  for (const key of keys) {
    const value = row[key];
    if (value !== null && value !== undefined && String(value).trim()) {
      return String(value).trim();
    }
  }
  return fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function rows(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) return payload.filter(isRecord);
  if (!isRecord(payload)) return [];
  const data = payload.data;
  if (Array.isArray(data)) return data.filter(isRecord);
  if (isRecord(data) && Array.isArray(data.data)) return data.data.filter(isRecord);
  if (Array.isArray(payload.resultados)) return payload.resultados.filter(isRecord);
  return [];
}

function unitFromRow(row: Record<string, unknown>): UnitName | null {
  const code = String(row.empresaCodigo ?? row.empresa ?? row.codigoEmpresa ?? "");
  const label = [
    row.nome,
    row.nomeFantasia,
    row.fantasia,
    row.unidade,
    row.empresaNome,
    row.razaoSocial,
  ]
    .map((item) => String(item ?? "").toLowerCase())
    .join(" ");

  if (code === "11495" || label.includes("posto vip") || label.includes(" vip")) return "VIP";
  if (code === "5555" || label.includes("casa caiada")) return "Casa Caiada";
  if (label.includes("posto real") || label.includes(" real")) return "Real";
  return null;
}

function cashKind(row: Record<string, unknown>): CashKind {
  const text = firstText(row, ["caixa", "tipoCaixa", "pdvDescricao", "descricao"], "").toLowerCase();
  if (text.includes("rest")) return "Restaurante";
  if (text.includes("conv") || text.includes("loja")) return "Conveniencia";
  return "Pista";
}

function statusFromRow(row: Record<string, unknown>): RegisterStatus {
  const raw = firstText(row, ["status", "situacao", "estado"], "").toLowerCase();
  if (raw.includes("abert")) return "Aberto";
  if (raw.includes("consolid")) return "Consolidado";
  return "Fechado";
}

function registerFromRow(row: Record<string, unknown>, index: number): CashRegister | null {
  const unidade = unitFromRow(row);
  if (!unidade) return null;

  const saldoEspecie = firstNumber(row, [
    "dinheiroApurado",
    "dinheiro",
    "valorDinheiro",
    "saldoEspecie",
    "totalDinheiro",
  ]);
  const dinheiroInformado =
    firstNumber(row, ["dinheiroApresentado", "valorInformado", "totalApresentado"]) || saldoEspecie;

  return {
    id: firstText(row, ["id", "caixaCodigo", "codigo"], `caixa-real-${index}`),
    unidade,
    data: firstText(row, ["data", "dataMovimento", "dataFechamento"], todaySaoPaulo()).slice(0, 10),
    caixa: cashKind(row),
    operador: firstText(row, ["operador", "funcionario", "funcionarioNome", "nomeFuncionario"], "Nao informado"),
    status: statusFromRow(row),
    vendasBrutas: firstNumber(row, [
      "vendasBrutas",
      "totalVendas",
      "vendaTotal",
      "valorTotal",
      "valor",
      "total",
    ]),
    despesas: firstNumber(row, ["despesaApurado", "despesa", "despesas", "totalDespesas"]),
    saldoEspecie,
    pagamentos: [
      { modalidade: "Dinheiro", valorSistema: saldoEspecie, valorInformado: dinheiroInformado },
      {
        modalidade: "PIX",
        valorSistema: firstNumber(row, ["pix", "valorPix"]),
        valorInformado: firstNumber(row, ["pixApresentado", "valorPixApresentado"]),
      },
      {
        modalidade: "Cartao Debito",
        valorSistema: firstNumber(row, ["cartaoDebito", "debito"]),
        valorInformado: firstNumber(row, ["cartaoDebitoApresentado", "debitoApresentado"]),
      },
      {
        modalidade: "Cartao Credito",
        valorSistema: firstNumber(row, ["cartaoCredito", "credito"]),
        valorInformado: firstNumber(row, ["cartaoCreditoApresentado", "creditoApresentado"]),
      },
      {
        modalidade: "Frotistas/Prazo",
        valorSistema: firstNumber(row, ["frotista", "prazo", "frotistasPrazo"]),
        valorInformado: firstNumber(row, ["frotistaApresentado", "prazoApresentado"]),
      },
    ],
  };
}

function expenseFromRow(row: Record<string, unknown>, index: number): AuditExpense | null {
  const unidade = unitFromRow(row);
  if (!unidade) return null;

  return {
    id: firstText(row, ["id", "codigo", "documento"], `despesa-real-${index}`),
    unidade,
    data: firstText(row, ["data", "dataMovimento"], todaySaoPaulo()).slice(0, 10),
    horario: firstText(row, ["hora", "horario"], "--:--").slice(0, 5),
    categoria: firstText(row, ["categoria", "tipoDespesa", "planoConta"], "") || null,
    valor: firstNumber(row, ["valor", "despesaApurado", "despesaApresentado"]),
    operador: firstText(row, ["operador", "funcionario", "funcionarioNome"], "Nao informado"),
    temAnexo: Boolean(row.documento || row.numeroDocumento || row.anexo || row.rastreabilidadeOk),
    justificativa: firstText(row, ["justificativa", "descricao", "planoConta"], "") || null,
  };
}

function onlyPresent<T>(value: T | null): value is T {
  return value !== null;
}

async function backendGet(path: string, params: URLSearchParams) {
  const response = await fetch(`${API_BASE}${path}?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

export async function GET(request: NextRequest) {
  const search = request.nextUrl.searchParams;
  const date = search.get("data") || todaySaoPaulo();
  const unidade = search.get("unidade") || "Todas";
  const params = new URLSearchParams({ dataInicial: date, dataFinal: date, limit: "80" });

  try {
    const [caixaRaw, expensesRaw] = await Promise.all([
      backendGet("/v1/caixa", params),
      backendGet("/v1/financial/expenses", params),
    ]);

    let caixas = rows(caixaRaw).map(registerFromRow).filter(onlyPresent);
    let despesas = rows(expensesRaw).map(expenseFromRow).filter(onlyPresent);

    if (unidade !== "Todas") {
      caixas = caixas.filter((item) => item.unidade === unidade);
      despesas = despesas.filter((item) => item.unidade === unidade);
    }

    return NextResponse.json({
      source: "webposto-api",
      lastUpdated: new Date().toISOString(),
      caixas,
      despesas,
    });
  } catch (error) {
    return NextResponse.json(
      {
        source: "webposto-api-unavailable",
        lastUpdated: new Date().toISOString(),
        error: error instanceof Error ? error.message : "Falha ao consultar API webPosto",
        caixas: [],
        despesas: [],
      },
      { status: 200 },
    );
  }
}
