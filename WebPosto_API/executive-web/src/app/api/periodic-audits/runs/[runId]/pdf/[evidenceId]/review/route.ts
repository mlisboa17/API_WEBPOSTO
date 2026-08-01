import { NextRequest, NextResponse } from "next/server";
const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";
export async function POST(request: NextRequest, context: { params: Promise<{ runId: string; evidenceId: string }> }) {
  const { runId, evidenceId } = await context.params;
  const response = await fetch(`${API}/api/v1/auditorias-periodicas/execucoes/${encodeURIComponent(runId)}/pdf/${encodeURIComponent(evidenceId)}/revisar`, {
    method: "POST", headers: { "Content-Type": "application/json", cookie: request.headers.get("cookie") || "" }, body: JSON.stringify(await request.json()),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
