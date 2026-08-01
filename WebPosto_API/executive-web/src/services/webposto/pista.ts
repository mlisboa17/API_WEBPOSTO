/**
 * Cliente REST v1 — Abastecimentos de pista (Quality Automação / LOGOS).
 *
 * Rotas oficiais (via proxy Next → FastAPI cache RAM):
 *   GET /api/abastecimentos/pendentes
 *   GET /api/abastecimentos/baixados
 */

export type StatusPista = "PENDENTE" | "BAIXADO";

export interface AbastecimentoRestV1 {
  idAbastecimento: number;
  uuid: string;
  dataHora: string;
  bico: number;
  tanque?: number | null;
  idProduto?: number | null;
  descricaoProduto: string;
  litros: number;
  precoUnitario: number;
  valorTotal: number;
  idFrentista?: number | null;
  nomeFrentista: string;
  status: StatusPista;
  reservado: boolean;
  idEmpresa: number;
  nomeEmpresa: string;
  idVenda?: number | null;
  documentoFiscal?: string | null;
  chaveAcesso?: string | null;
  formaPagamento?: string | null;
  cliente?: string | null;
  dataHoraBaixa?: string | null;
}

export interface FilialDiaResumo {
  idEmpresa: number;
  nomeEmpresa: string;
  totalAbastecimentos: number;
  totalLitros: number;
  totalValor: number;
  totalPendentes: number;
  totalBaixados: number;
}

export interface ResumoDiaPista {
  totalAbastecimentos: number;
  totalLitros: number;
  totalValor: number;
  totalPendentes: number;
  totalBaixados: number;
  porFilial: FilialDiaResumo[];
}

export interface TotaisDiaPista {
  faturamentoTotal: number;
  volumetriaTotalLitros: number;
  qtdTotalAbastecimentos: number;
  pvmMedio?: number;
  valorCartoesDia?: number;
  qtdCartoesDia?: number;
  alertasCriticosRetencao?: number;
  valorCriticoRetencao?: number;
}

export interface FraudeKpiResumo {
  alertasCriticos: number;
  valorCriticoRetencao?: number;
  valorCartoesDia?: number;
  qtdCartoesDia?: number;
  limiarCriticoMinutos?: number;
}

export interface KpisResumoResponse {
  success: boolean;
  synthetic?: boolean;
  fromCache?: boolean;
  fonte?: string;
  ultimaSincronizacaoIso?: string | null;
  totaisDia: TotaisDiaPista;
  fraude?: FraudeKpiResumo;
  resumoDia?: ResumoDiaPista | null;
  error?: string | null;
}

export interface ListaAbastecimentosResponse {
  success: boolean;
  synthetic?: boolean;
  fonte?: string;
  endpoint?: string;
  status?: string;
  total: number;
  pagina?: number;
  limite?: number;
  items: AbastecimentoRestV1[];
  resumoDia?: ResumoDiaPista | null;
  totaisDia?: TotaisDiaPista | null;
  ultimaSincronizacaoIso?: string | null;
  totalRealDia?: number | null;
  volumetriaTotalDia?: number | null;
  fromCache?: boolean;
  observacoes?: string[];
  error?: string | null;
}

const FETCH_TIMEOUT_MS = 6_000;

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** Data local YYYY-MM-DD (evita UTC virar D+1 à noite no Brasil). */
export function hojeLocalIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function emptyLista(error: string, observacoes: string[] = []): ListaAbastecimentosResponse {
  return {
    success: false,
    total: 0,
    items: [],
    totaisDia: {
      faturamentoTotal: 0,
      volumetriaTotalLitros: 0,
      qtdTotalAbastecimentos: 0,
    },
    resumoDia: emptyResumo(),
    error,
    observacoes: observacoes.length ? observacoes : [error],
  };
}

function emptyResumo(): ResumoDiaPista {
  return {
    totalAbastecimentos: 0,
    totalLitros: 0,
    totalValor: 0,
    totalPendentes: 0,
    totalBaixados: 0,
    porFilial: [],
  };
}

function emptyTotais(): TotaisDiaPista {
  return {
    faturamentoTotal: 0,
    volumetriaTotalLitros: 0,
    qtdTotalAbastecimentos: 0,
    pvmMedio: 0,
    valorCartoesDia: 0,
    qtdCartoesDia: 0,
    alertasCriticosRetencao: 0,
    valorCriticoRetencao: 0,
  };
}

/** KPIs do dia — leitura exclusiva do cache RAM (<50ms). */
export async function fetchKpisResumo(): Promise<KpisResumoResponse> {
  try {
    const res = await fetch("/api/abastecimentos/kpis/resumo", {
      cache: "no-store",
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
    const raw = (await res.json()) as KpisResumoResponse;
    const totais = raw?.totaisDia && typeof raw.totaisDia === "object"
      ? {
          ...emptyTotais(),
          ...raw.totaisDia,
          faturamentoTotal: Number(raw.totaisDia.faturamentoTotal ?? 0) || 0,
          volumetriaTotalLitros: Number(raw.totaisDia.volumetriaTotalLitros ?? 0) || 0,
          qtdTotalAbastecimentos: Number(raw.totaisDia.qtdTotalAbastecimentos ?? 0) || 0,
          pvmMedio: Number(raw.totaisDia.pvmMedio ?? 0) || 0,
          valorCartoesDia: Number(raw.totaisDia.valorCartoesDia ?? 0) || 0,
          qtdCartoesDia: Number(raw.totaisDia.qtdCartoesDia ?? 0) || 0,
          alertasCriticosRetencao: Number(raw.totaisDia.alertasCriticosRetencao ?? 0) || 0,
          valorCriticoRetencao: Number(raw.totaisDia.valorCriticoRetencao ?? 0) || 0,
        }
      : emptyTotais();
    return {
      success: raw?.success !== false,
      synthetic: Boolean(raw?.synthetic),
      fromCache: Boolean(raw?.fromCache),
      fonte: raw?.fonte,
      ultimaSincronizacaoIso: raw?.ultimaSincronizacaoIso ?? null,
      totaisDia: totais,
      fraude: raw?.fraude,
      resumoDia: raw?.resumoDia ?? null,
      error: raw?.error ?? null,
    };
  } catch (e: unknown) {
    return {
      success: false,
      totaisDia: emptyTotais(),
      fraude: { alertasCriticos: 0 },
      error: e instanceof Error ? e.message : "Falha ao carregar KPIs",
    };
  }
}

/** Normaliza qualquer envelope (array cru, cache, erro) para o contrato LOGOS. */
function normalizeLista(raw: unknown, httpStatus: number, url: string): ListaAbastecimentosResponse {
  if (Array.isArray(raw)) {
    return {
      success: true,
      total: raw.length,
      items: raw as AbastecimentoRestV1[],
      totaisDia: emptyTotais(),
      resumoDia: emptyResumo(),
    };
  }

  const data = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const items = Array.isArray(data.items)
    ? (data.items as AbastecimentoRestV1[])
    : Array.isArray(data)
      ? (data as unknown as AbastecimentoRestV1[])
      : [];

  const totaisRaw = data.totaisDia as TotaisDiaPista | undefined;
  const totaisDia: TotaisDiaPista =
    totaisRaw && typeof totaisRaw === "object"
      ? {
          ...emptyTotais(),
          faturamentoTotal: Number(totaisRaw.faturamentoTotal ?? 0) || 0,
          volumetriaTotalLitros: Number(totaisRaw.volumetriaTotalLitros ?? 0) || 0,
          qtdTotalAbastecimentos: Number(totaisRaw.qtdTotalAbastecimentos ?? 0) || 0,
          pvmMedio: Number(totaisRaw.pvmMedio ?? 0) || 0,
          valorCartoesDia: Number(totaisRaw.valorCartoesDia ?? 0) || 0,
          qtdCartoesDia: Number(totaisRaw.qtdCartoesDia ?? 0) || 0,
          alertasCriticosRetencao: Number(totaisRaw.alertasCriticosRetencao ?? 0) || 0,
          valorCriticoRetencao: Number(totaisRaw.valorCriticoRetencao ?? 0) || 0,
        }
      : emptyTotais();

  const resumoRaw = data.resumoDia;
  let resumoDia: ResumoDiaPista = emptyResumo();
  if (resumoRaw && typeof resumoRaw === "object") {
    const r = resumoRaw as ResumoDiaPista;
    resumoDia = {
      totalAbastecimentos: Number(r.totalAbastecimentos ?? 0) || 0,
      totalLitros: Number(r.totalLitros ?? 0) || 0,
      totalValor: Number(r.totalValor ?? 0) || 0,
      totalPendentes: Number(r.totalPendentes ?? 0) || 0,
      totalBaixados: Number(r.totalBaixados ?? 0) || 0,
      porFilial: Array.isArray(r.porFilial) ? r.porFilial : [],
    };
  }

  const error =
    typeof data.error === "string" && data.error
      ? data.error
      : httpStatus >= 400
        ? `HTTP ${httpStatus} em ${url}`
        : null;

  return {
    success: data.success !== false && !error,
    synthetic: Boolean(data.synthetic),
    fonte: typeof data.fonte === "string" ? data.fonte : undefined,
    endpoint: typeof data.endpoint === "string" ? data.endpoint : undefined,
    status: typeof data.status === "string" ? data.status : undefined,
    total: Number(data.total ?? items.length) || 0,
    pagina: Number(data.pagina ?? 1) || 1,
    limite: Number(data.limite ?? items.length) || items.length,
    items,
    resumoDia,
    totaisDia,
    ultimaSincronizacaoIso:
      typeof data.ultimaSincronizacaoIso === "string" ? data.ultimaSincronizacaoIso : null,
    totalRealDia:
      data.totalRealDia != null
        ? Number(data.totalRealDia)
        : totaisDia.qtdTotalAbastecimentos || resumoDia.totalAbastecimentos,
    volumetriaTotalDia:
      data.volumetriaTotalDia != null
        ? Number(data.volumetriaTotalDia)
        : totaisDia.volumetriaTotalLitros || resumoDia.totalLitros,
    fromCache: Boolean(data.fromCache),
    observacoes: Array.isArray(data.observacoes)
      ? (data.observacoes as string[])
      : error
        ? [error]
        : [],
    error,
  };
}

async function getJson(url: string): Promise<ListaAbastecimentosResponse> {
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
    let raw: unknown;
    try {
      raw = await res.json();
    } catch {
      return emptyLista(`JSON inválido (HTTP ${res.status}) em ${url}`, [`HTTP ${res.status}`]);
    }
    return normalizeLista(raw, res.status, url);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Falha de rede";
    return emptyLista(`${message} (${url})`);
  }
}

/** Pista em aberto — aguardando baixa no PDV. */
export async function fetchAbastecimentosPendentes(opts?: {
  idEmpresa?: number;
  idBico?: number;
}): Promise<ListaAbastecimentosResponse> {
  const query = qs({
    idEmpresa: opts?.idEmpresa,
    idBico: opts?.idBico,
  });
  return getJson(`/api/abastecimentos/pendentes${query}`);
}

/** Abastecimentos faturados/liquidados no período. */
export async function fetchAbastecimentosBaixados(opts?: {
  idEmpresa?: number;
  dataInicio?: string;
  dataFim?: string;
  pagina?: number;
  limite?: number;
}): Promise<ListaAbastecimentosResponse> {
  const query = qs({
    idEmpresa: opts?.idEmpresa,
    dataInicio: opts?.dataInicio,
    dataFim: opts?.dataFim,
    pagina: opts?.pagina ?? 1,
    limite: opts?.limite ?? 100,
  });
  return getJson(`/api/abastecimentos/baixados${query}`);
}

export interface FeedVivoPistaResult {
  items: AbastecimentoRestV1[];
  pendentes: AbastecimentoRestV1[];
  baixados: AbastecimentoRestV1[];
  resumoDia: ResumoDiaPista;
  totaisDia: TotaisDiaPista;
  totalDia: number;
  ultimaSincronizacaoIso: string | null;
  fromCache: boolean;
  fonte: string;
  observacoes: string[];
  error?: string | null;
}

/** Feed vivo do Cockpit: pendentes + últimos baixados + resumoDia completo. */
export async function fetchFeedVivoPista(opts?: {
  idEmpresa?: number;
  dataInicio?: string;
  dataFim?: string;
  limiteBaixados?: number;
}): Promise<FeedVivoPistaResult> {
  const hoje = opts?.dataInicio || hojeLocalIso();
  const settled = await Promise.allSettled([
    fetchAbastecimentosPendentes({ idEmpresa: opts?.idEmpresa }),
    fetchAbastecimentosBaixados({
      idEmpresa: opts?.idEmpresa,
      dataInicio: opts?.dataInicio || hoje,
      dataFim: opts?.dataFim || hoje,
      pagina: 1,
      limite: opts?.limiteBaixados ?? 80,
    }),
  ]);

  const pend =
    settled[0].status === "fulfilled"
      ? settled[0].value
      : emptyLista(String(settled[0].reason || "Falha pendentes"));
  const baix =
    settled[1].status === "fulfilled"
      ? settled[1].value
      : emptyLista(String(settled[1].reason || "Falha baixados"));

  const pendentes = Array.isArray(pend.items) ? pend.items : [];
  const baixados = Array.isArray(baix.items) ? baix.items : [];
  const seen = new Set<string>();
  const items: AbastecimentoRestV1[] = [];

  for (const row of [...pendentes, ...baixados].sort((a, b) =>
    String(b?.dataHora || "").localeCompare(String(a?.dataHora || ""))
  )) {
    if (!row || typeof row !== "object") continue;
    const key = `${row.idEmpresa}:${row.idAbastecimento}`;
    if (seen.has(key)) continue;
    seen.add(key);
    items.push(row);
  }

  const resumoDia = mergeResumoComPendentes(baix.resumoDia || emptyResumo(), pendentes);
  const totaisDia: TotaisDiaPista = baix.totaisDia?.qtdTotalAbastecimentos
    ? baix.totaisDia
    : {
        faturamentoTotal: resumoDia.totalValor,
        volumetriaTotalLitros: resumoDia.totalLitros,
        qtdTotalAbastecimentos: resumoDia.totalAbastecimentos,
      };

  const totalDia =
    baix.totalRealDia ??
    totaisDia.qtdTotalAbastecimentos ??
    resumoDia.totalAbastecimentos ??
    baix.total ??
    items.length;

  return {
    items,
    pendentes,
    baixados,
    resumoDia,
    totaisDia,
    totalDia,
    ultimaSincronizacaoIso:
      baix.ultimaSincronizacaoIso || pend.ultimaSincronizacaoIso || null,
    fromCache: Boolean(baix.fromCache || pend.fromCache),
    fonte: baix.fonte || pend.fonte || "REST_v1_Abastecimentos",
    observacoes: [...(pend.observacoes || []), ...(baix.observacoes || [])],
    error: pend.error || baix.error,
  };
}

/** Segundos desde ultimaSincronizacaoIso (null se desconhecido). */
export function segundosDesdeSync(iso?: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((Date.now() - t) / 1000));
}

function mergeResumoComPendentes(
  base: ResumoDiaPista,
  pendentes: AbastecimentoRestV1[]
): ResumoDiaPista {
  if (!pendentes.length) {
    if (base.totalAbastecimentos > 0 || base.porFilial?.length) return base;
    return base;
  }
  if ((base.totalPendentes || 0) >= pendentes.length) return base;

  const por = new Map<number, FilialDiaResumo>();
  for (const f of base.porFilial || []) {
    por.set(f.idEmpresa, { ...f });
  }
  for (const p of pendentes) {
    if (!p) continue;
    const cur = por.get(p.idEmpresa) || {
      idEmpresa: p.idEmpresa,
      nomeEmpresa: p.nomeEmpresa || `Empresa ${p.idEmpresa}`,
      totalAbastecimentos: 0,
      totalLitros: 0,
      totalValor: 0,
      totalPendentes: 0,
      totalBaixados: 0,
    };
    cur.totalPendentes += 1;
    cur.totalAbastecimentos += 1;
    cur.totalLitros = Math.round((cur.totalLitros + (p.litros || 0)) * 1000) / 1000;
    cur.totalValor = Math.round((cur.totalValor + (p.valorTotal || 0)) * 100) / 100;
    por.set(p.idEmpresa, cur);
  }
  const porFilial = Array.from(por.values()).sort((a, b) => a.idEmpresa - b.idEmpresa);
  return {
    totalAbastecimentos: porFilial.reduce((s, f) => s + f.totalAbastecimentos, 0),
    totalLitros: Math.round(porFilial.reduce((s, f) => s + f.totalLitros, 0) * 1000) / 1000,
    totalValor: Math.round(porFilial.reduce((s, f) => s + f.totalValor, 0) * 100) / 100,
    totalPendentes: porFilial.reduce((s, f) => s + f.totalPendentes, 0),
    totalBaixados: porFilial.reduce((s, f) => s + f.totalBaixados, 0),
    porFilial,
  };
}

export function horaFromDataHora(dataHora?: string | null): string {
  if (!dataHora) return "--:--";
  const text = String(dataHora);
  if (text.includes("T")) {
    const part = text.split("T")[1] ?? "";
    return part.slice(0, 8) || "--:--";
  }
  if (text.includes(" ")) {
    const part = text.split(" ")[1] ?? "";
    return part.slice(0, 8) || "--:--";
  }
  return text.slice(0, 8) || "--:--";
}

/** Volumetria oficial: 3 casas decimais. */
export function formatLitros(litros?: number | null): string {
  return `${(litros ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  })} L`;
}
