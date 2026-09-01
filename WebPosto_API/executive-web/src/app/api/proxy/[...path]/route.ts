import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";
const COPILOT_API = process.env.WEBPOSTO_COPILOT_API_URL || "http://127.0.0.1:8095";
const TIMEOUT_MS = 30000;
/** Rotas que consolidam 3 filiais via webPosto — precisam de timeout maior. */
const HEAVY_PATH_TIMEOUT_MS = 180000;
const HEAVY_PATH_MARKERS = [
  "data-audit",
  "branch-benchmark",
  "dre-intelligence",
  "dre-multidimensional",
  "health-synthesis",
  "audit/card-fraud",
  "card-fraud",
  "expenses/details",
  "expense-entry/drill-down",
  "sales/composition",
  "sales/analytics",
  "sales/elasticity",
  "logistics/efficiency",
  "inventory-prediction",
  "fuel-loss",
  "briefing",
  "dashboard/bundle",
  "consolidated-report",
  "cash-reconciliation",
  "payment-methods",
  "dre-complete",
  "finance/center",
  "price-update",
  "operational/price-update",
  "product-registration",
  "operational/product-registration",
  "fiscal-models",
  "operational/fiscal-models",
  "dfe",
  "operational/dfe",
];

const OFFLINE_ERROR = "Serviço temporariamente indisponível";

type RouteParams = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteParams) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path || [], "GET");
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path || [], "POST");
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path || [], "PATCH");
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  const resolvedParams = await params;
  return handleRequest(request, resolvedParams.path || [], "DELETE");
}

function isConnectionFailure(message: string, error: unknown): boolean {
  const hay = `${message} ${error instanceof Error ? error.name : ""}`.toLowerCase();
  return (
    hay.includes("econnrefused")
    || hay.includes("econnreset")
    || hay.includes("enotfound")
    || hay.includes("etimedout")
    || hay.includes("eai_again")
    || hay.includes("fetch failed")
    || hay.includes("network")
    || hay.includes("aborted")
    || hay.includes("aborterror")
    || hay.includes("timeout")
    || hay.includes("timed out")
  );
}

/** Shapes vazias para rotas críticas — evitam crash de UI quando data !== null. */
function getOfflineDataShape(path: string): Record<string, unknown> | unknown[] | null {
  if (path.includes("inventory-prediction")) {
    return {
      empresa_codigo: 0,
      empresa_nome: "Offline",
      data_calculo: new Date().toISOString().split("T")[0],
      dias_cobertura: 3,
      lead_time_horas: 24,
      predicoes: [],
      total_sugestao_compra_litros: 0,
      tanques_com_alerta: 0,
      tanques_urgentes: 0,
      observacoes: [OFFLINE_ERROR],
    };
  }
  if (path.includes("fuel-loss") || path.includes("tanks")) {
    return {
      tanks: [],
      summary: null,
      observacoes: [OFFLINE_ERROR],
    };
  }
  if (path.includes("cockpit-live") || path.includes("abastecimentos")) {
    return {
      periodo: { inicio: "", fim: "" },
      filiais: [],
      abastecimentos: [],
    };
  }
  if (path.includes("consolidated-report")) {
    return {
      gerado_em: new Date().toISOString(),
      sprint: "offline",
      periodo_principal: { inicio: "", fim: "" },
      filiais_monitoradas: [],
      bloco_1_combustiveis: { resumo: { total_litros: 0, total_valor: 0 }, por_produto: [] },
      bloco_3_margens: { margem_bruta_total: 0, margem_liquida: 0, margem_media_litro: 0 },
      bloco_4_conveniencia: { receita_total: 0, margem_bruta: 0 },
      bloco_5_dre: {
        departamentos_confirmados: [],
        resumo_auto_classificacao: { total_auto_classificadas: 0, remanescentes_nao_classificadas: 0 },
      },
      bloco_6_despesas: { total: 0, por_categoria: [], auto_classificadas: [] },
      bloco_9_anomalias: {
        titulo: "",
        status: "",
        divergencias_caixa: {},
        detalhamento_pagamento: [],
        rombo_por_operador_turno: [],
        alertas: [],
        auditoria_pista: null,
      },
    };
  }
  if (path.includes("dashboard/bundle")) {
    return {
      period: { start: "", end: "" },
      synthesis: {},
      active_alerts: [],
      cash_cycle: {},
    };
  }
  if (path.includes("alerts") || path.includes("alert-history")) {
    return [];
  }
  if (path.includes("data-audit")) {
    return {
      periodo: { inicio: "", fim: "" },
      filiais: [],
      consolidado: {},
      mensagem: OFFLINE_ERROR,
    };
  }
  if (path.includes("audit/cashier") || path.endsWith("cashier")) {
    return {
      resumoDia: {
        totalEsperado: 0,
        totalDeclarado: 0,
        divergenciaTotal: 0,
        sobras: 0,
        faltas: 0,
      },
      fechamentosPorTurno: [],
      quebrasPorFormaPagamento: [],
      totalFechamentos: 0,
      hasMore: false,
      observacoes: [OFFLINE_ERROR],
    };
  }
  if (path.includes("card-fraud") || (path.includes("audit/") && !path.includes("cashier"))) {
    return {
      fonte: "offline",
      endpoint: "",
      periodo: { inicio: "", fim: "" },
      limiarRetencaoMinutos: 15,
      limiarCriticoMinutos: 30,
      resumo: {
        totalAgrupamentosSuspeitos: 0,
        totalCriticos: 0,
        totalAtencao: 0,
        valorTotalRetidoCartoes: 0,
        valorCritico: 0,
        frentistaMaiorIncidencia: "SEM REGISTRO",
        frentistaMaiorIncidenciaQtd: 0,
        abastecimentosCriticosBanner: 0,
      },
      ocorrencias: [],
      bannerAlerta: null,
      observacoes: [OFFLINE_ERROR],
    };
  }
  return null;
}

function offlinePayload(path: string, detail?: string) {
  return {
    success: false as const,
    error: OFFLINE_ERROR,
    data: getOfflineDataShape(path),
    offline: true,
    detail: detail ? detail.slice(0, 220) : undefined,
  };
}

async function handleRequest(request: NextRequest, pathSegments: string[], method: string) {
  const path = pathSegments.join("/");
  const url = new URL(request.url);
  const isCopilot =
    path.startsWith("executive-copilot") || url.searchParams.get("demo") === "copilot";
  const apiBase = isCopilot ? COPILOT_API : API;
  const isBareHealth = path === "health" || path === "ready";
  const isBareAuthMe = isCopilot && path === "auth/me";
  const targetUrl =
    isBareHealth || isBareAuthMe
      ? `${apiBase}/${path}${url.search}`
      : `${apiBase}/api/v1/${path}${url.search}`;

  console.log(`[Proxy] ${method} ${path} -> ${targetUrl}`);

  try {
    const controller = new AbortController();
    const timeoutMs = HEAVY_PATH_MARKERS.some((m) => path.includes(m))
      ? HEAVY_PATH_TIMEOUT_MS
      : TIMEOUT_MS;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const incomingContentType = request.headers.get("content-type") || "";
    const isMultipart = incomingContentType.includes("multipart/form-data");
    const headers: Record<string, string> = {
      cookie: request.headers.get("cookie") || "",
    };
    // Multipart: NÃO definir Content-Type manualmente — o fetch gera o boundary.
    if (!isMultipart && method !== "GET" && method !== "HEAD") {
      headers["Content-Type"] = incomingContentType || "application/json";
    }

    const options: RequestInit = {
      method,
      headers,
      cache: "no-store",
      signal: controller.signal,
    };

    if (method !== "GET" && method !== "HEAD") {
      try {
        if (isMultipart) {
          // Reconstroi FormData (arquivo + campos) sem converter para JSON.
          options.body = await request.formData();
        } else {
          const body = await request.text();
          if (body) options.body = body;
        }
      } catch {
        // Ignora corpo se não houver
      }
    }

    const response = await fetch(targetUrl, options);
    clearTimeout(timeoutId);

    console.log(`[Proxy] ${method} ${path} -> ${response.status}`);

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      // Preserva UTF-8 (evita mojibake NestlÃ© / InvÃ¡lidas na UI).
      const text = await response.text();
      return new NextResponse(text, {
        status: response.status,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store",
          ...(response.headers.get("x-webposto-offline-mode")
            ? { "X-WebPosto-Offline-Mode": "true" }
            : {}),
        },
      });
    }
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "Content-Type": contentType
          ? (contentType.includes("charset") ? contentType : `${contentType}; charset=utf-8`)
          : "text/plain; charset=utf-8",
      },
    });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Erro na ponte de API";
    console.error(`[Proxy] ERROR ${method} ${path}:`, message);

    const status = isConnectionFailure(message, e) ? 503 : 502;
    const payload = offlinePayload(path, message);
    console.log(`[Proxy] Returning offline ${status} for ${path}`);
    return NextResponse.json(payload, { status });
  }
}
