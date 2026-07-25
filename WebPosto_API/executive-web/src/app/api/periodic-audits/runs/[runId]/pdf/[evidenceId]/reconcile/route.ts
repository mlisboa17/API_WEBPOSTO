import { NextRequest, NextResponse } from "next/server";
const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8000";
export async function POST(request: NextRequest, context: { params: Promise<{ runId: string; evidenceId: string }> }) {
  const { runId, evidenceId } = await context.params;
  const response = await fetch(`${API}/api/v1/auditorias-periodicas/execucoes/${encodeURIComponent(runId)}/pdf/${encodeURIComponent(evidenceId)}/reconciliar`, {
    method: "POST", headers: { cookie: request.headers.get("cookie") || "" }, signal: AbortSignal.timeout(180000),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
