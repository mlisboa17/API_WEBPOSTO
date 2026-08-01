import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const dataInicial = searchParams.get("dataInicial");
  const dataFinal = searchParams.get("dataFinal");
  const empresaCodigo = searchParams.get("empresaCodigo");

  const query = new URLSearchParams();
  if (dataInicial) query.set("dataInicial", dataInicial);
  if (dataFinal) query.set("dataFinal", dataFinal);
  if (empresaCodigo) query.set("empresaCodigo", empresaCodigo);

  try {
    const response = await fetch(`${API}/api/v1/executive/dashboard/bundle?${query}`, {
      cache: "no-store",
      headers: { 
        cookie: request.headers.get("cookie") || "",
        "Content-Type": "application/json"
      },
    });

    if (response.status === 401) {
      return NextResponse.json({ success: false, error: "Não autenticado" }, { status: 401 });
    }

    const data = await response.json() as unknown;
    return NextResponse.json(data, { status: response.status });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Erro na comunicação com o servidor";
    console.error("Error fetching dashboard bundle:", message);
    return NextResponse.json(
      { success: false, error: "Erro na comunicação com o servidor: " + message },
      { status: 500 }
    );
  }
}
