import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

export async function GET(request: NextRequest, context: { params: Promise<{ runId: string }> }) {
  const { runId } = await context.params;
  const response = await fetch(
    `${API}/api/v1/auditorias-periodicas/execucoes/${encodeURIComponent(runId)}/dossie-integridade`,
    { cache: "no-store", headers: { cookie: request.headers.get("cookie") || "" } },
  );
  return NextResponse.json(await response.json(), { status: response.status });
}
