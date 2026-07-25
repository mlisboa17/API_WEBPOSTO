import { NextRequest, NextResponse } from "next/server";
const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8000";
export async function POST(request: NextRequest, context: { params: Promise<{ runId: string }> }) {
  const { runId } = await context.params;
  const response = await fetch(`${API}/api/v1/auditorias-periodicas/execucoes/${encodeURIComponent(runId)}/pdf`, {
    method: "POST", headers: { "content-type": "application/pdf", "x-filename": request.headers.get("x-filename") || "prestacao-contas.pdf", cookie: request.headers.get("cookie") || "" }, body: await request.arrayBuffer(),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
