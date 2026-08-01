import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";
const TIMEOUT_MS = 30000;
/** Rotas que consolidam 3 filiais via webPosto — precisam de timeout maior. */
const HEAVY_PATH_TIMEOUT_MS = 180000;
const HEAVY_PATH_MARKERS = [
  "data-audit",
  "audit/card-fraud",
  "card-fraud",
  "expenses/details",
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
];

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

function getFallbackResponse(path: string): Record<string, unknown> | unknown[] | null {
  if (path.includes("inventory-prediction")) {
    return {
      success: true,
      empresa_codigo: 0,
      empresa_nome: "Fallback",
      data_calculo: new Date().toISOString().split("T")[0],
      dias_cobertura: 3,
      lead_time_horas: 24,
      predicoes: [],
      total_sugestao_compra_litros: 0,
      tanques_com_alerta: 0,
      tanques_urgentes: 0,
      observacoes: ["Backend indisponivel - usando fallback"],
    };
  }
  if (path.includes("fuel-loss") || path.includes("tanks")) {
    return {
      success: true,
      tanks: [],
      summary: null,
      observacoes: ["Backend indisponivel - usando fallback"],
    };
  }
  if (path.includes("cockpit-live") || path.includes("abastecimentos")) {
    return {
      success: true,
      periodo: { inicio: "", fim: "" },
      filiais: [],
      abastecimentos: [],
      error: null,
    };
  }
  if (path.includes("consolidated-report")) {
    return {
      gerado_em: new Date().toISOString(),
      sprint: "fallback",
      periodo_principal: { inicio: "", fim: "" },
      filiais_monitoradas: [],
      bloco_1_combustiveis: { resumo: { total_litros: 0, total_valor: 0 }, por_produto: [] },
      bloco_3_margens: { margem_bruta_total: 0, margem_liquida: 0, margem_media_litro: 0 },
      bloco_4_conveniencia: { receita_total: 0, margem_bruta: 0 },
      bloco_5_dre: { departamentos_confirmados: [], resumo_auto_classificacao: { total_auto_classificadas: 0, remanescentes_nao_classificadas: 0 } },
      bloco_6_despesas: { total: 0, por_categoria: [], auto_classificadas: [] },
      bloco_9_anomalias: { titulo: "", status: "", divergencias_caixa: {}, detalhamento_pagamento: [], rombo_por_operador_turno: [], alertas: [], auditoria_pista: null },
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
      success: true,
      data: {
        periodo: { inicio: "", fim: "" },
        filiais: [],
        consolidado: {},
        success: false,
        mensagem: "Backend indisponivel - fallback data-audit",
      },
    };
  }
  if (path.includes("audit/cashier") || path.endsWith("cashier")) {
    return {
      success: true,
      fromCache: true,
      data: {
        success: false,
        fromCache: true,
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
        observacoes: ["Backend indisponivel — cache de caixas vazio"],
      },
    };
  }
  if (path.includes("card-fraud") || (path.includes("audit/") && !path.includes("cashier"))) {
    return {
      success: true,
      synthetic: false,
      data: {
        success: false,
        synthetic: false,
        fonte: "AbastecimentoRede",
        endpoint: "/INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE",
        periodo: { inicio: "", fim: "" },
        limiarRetencaoMinutos: 15,
        limiarCriticoMinutos: 30,
        resumo: {
          totalAgrupamentosSuspeitos: 0,
          totalCriticos: 0,
          totalAtencao: 0,
          valorTotalRetidoCartoes: 0,
          valorCritico: 0,
          frentistaMaiorIncidencia: "SEM REGISTRO NO PERIODO",
          frentistaMaiorIncidenciaQtd: 0,
          abastecimentosCriticosBanner: 0,
        },
        ocorrencias: [],
        bannerAlerta: null,
        observacoes: ["Backend indisponivel — lista vazia (synthetic: false)"],
      },
    };
  }
  return null;
}

async function handleRequest(request: NextRequest, pathSegments: string[], method: string) {
  const path = pathSegments.join("/");
  const url = new URL(request.url);
  const targetUrl = `${API}/api/v1/${path}${url.search}`;

  console.log(`[Proxy] ${method} ${path} -> ${targetUrl}`);

  try {
    const controller = new AbortController();
    const timeoutMs = HEAVY_PATH_MARKERS.some((m) => path.includes(m))
      ? HEAVY_PATH_TIMEOUT_MS
      : TIMEOUT_MS;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const options: RequestInit = {
      method,
      headers: {
        cookie: request.headers.get("cookie") || "",
        "Content-Type": "application/json",
      },
      cache: "no-store",
      signal: controller.signal,
    };

    if (method !== "GET" && method !== "HEAD") {
      try {
        const body = await request.text();
        if (body) options.body = body;
      } catch {
        // Ignora corpo se não houver
      }
    }

    const response = await fetch(targetUrl, options);
    clearTimeout(timeoutId);

    console.log(`[Proxy] ${method} ${path} -> ${response.status}`);
    
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const data = await response.json() as unknown;
      return NextResponse.json(data, { status: response.status });
    } else {
      const text = await response.text();
      return new NextResponse(text, { 
        status: response.status,
        headers: { "Content-Type": contentType || "text/plain" }
      });
    }
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Erro na ponte de API";
    console.error(`[Proxy] ERROR ${method} ${path}:`, message);
    
    const fallback = getFallbackResponse(path);
    if (fallback) {
      console.log(`[Proxy] Returning fallback for ${path}`);
      return NextResponse.json(fallback, { status: 200 });
    }
    
    return NextResponse.json(
      { success: false, error: "Backend indisponivel: " + message, data: null },
      { status: 200 }
    );
  }
}
