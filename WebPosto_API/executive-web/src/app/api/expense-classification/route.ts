import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";
const ENDPOINT = `${API}/api/v1/finance/director-reconciliation/expense-classifications`;

export async function GET() {
  const response = await fetch(ENDPOINT, { cache: "no-store" });
  return NextResponse.json(await response.json(), { status: response.status });
}

export async function POST(request: NextRequest) {
  const endpoint = request.nextUrl.searchParams.get("bulk") === "1" ? `${ENDPOINT}/batch` : ENDPOINT;
  const response = await fetch(endpoint, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(await request.json()),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}

export async function DELETE(request: NextRequest) {
  const factId = request.nextUrl.searchParams.get("factId");
  const accountCode = request.nextUrl.searchParams.get("accountCode");
  if (!factId) return NextResponse.json({ detail: "factId obrigatório" }, { status: 400 });
  const query = accountCode ? `?managementAccountCode=${encodeURIComponent(accountCode)}` : "";
  const response = await fetch(`${ENDPOINT}/${encodeURIComponent(factId)}${query}`, { method: "DELETE" });
  return NextResponse.json(await response.json(), { status: response.status });
}
