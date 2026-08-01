import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const targetUrl = `${API}/api/v1/operational/cockpit-live${url.search}`;

  try {
    const response = await fetch(targetUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    const data = await response.json();
    
    return NextResponse.json(data, { status: response.ok ? 200 : response.status });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Erro na ponte de API";
    console.error(`Cockpit API error:`, message);
    return NextResponse.json(
      { 
        success: true, 
        periodo: { inicio: new Date().toISOString().split("T")[0], fim: new Date().toISOString().split("T")[0] },
        filiais: [],
        abastecimentos: [], 
        error: message 
      },
      { status: 200 }
    );
  }
}
