import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

/** Backend serve do cache RAM — timeout curto. */
export const maxDuration = 30;
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const targetUrl = `${API}/api/v1/abastecimentos/pendentes${url.search}`;

  try {
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });

    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = {
        success: false,
        status: "PENDENTE",
        total: 0,
        items: [],
        error: `Resposta inválida do backend (HTTP ${response.status})`,
        observacoes: [`HTTP ${response.status} sem JSON`],
      };
    }

    return NextResponse.json(data, { status: 200 });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Erro na ponte de API";
    console.error("[abastecimentos/pendentes]", message, "target=", targetUrl);
    return NextResponse.json(
      {
        success: false,
        status: "PENDENTE",
        total: 0,
        items: [],
        error: message,
        observacoes: [message],
      },
      { status: 200 }
    );
  }
}
