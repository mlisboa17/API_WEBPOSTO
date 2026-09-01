import { NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

export const maxDuration = 30;
export const dynamic = "force-dynamic";

export async function GET() {
  const targetUrl = `${API}/api/v1/abastecimentos/kpis/resumo`;
  try {
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Erro na ponte de API";
    return NextResponse.json(
      {
        success: false,
        synthetic: false,
        fromCache: false,
        totaisDia: {
          faturamentoTotal: 0,
          volumetriaTotalLitros: 0,
          qtdTotalAbastecimentos: 0,
          pvmMedio: 0,
          valorCartoesDia: 0,
          qtdCartoesDia: 0,
          alertasCriticosRetencao: 0,
          valorCriticoRetencao: 0,
        },
        fraude: { alertasCriticos: 0 },
        error: message,
      },
      { status: 200 }
    );
  }
}
