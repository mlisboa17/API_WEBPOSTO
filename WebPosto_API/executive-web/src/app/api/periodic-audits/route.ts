import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";
const ENDPOINT = `${API}/api/v1/auditorias-periodicas/ciclos`;

export async function GET() {
  const response = await fetch(ENDPOINT, { cache: "no-store" });
  return NextResponse.json(await response.json(), { status: response.status });
}

export async function POST(request: NextRequest) {
  const response = await fetch(ENDPOINT, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(await request.json()),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}

export async function PATCH(request: NextRequest) {
  const { id, ...body } = await request.json();
  const response = await fetch(`${ENDPOINT}/${encodeURIComponent(String(id))}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
