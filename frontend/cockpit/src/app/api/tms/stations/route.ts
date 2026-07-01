import { NextRequest, NextResponse } from "next/server";

const SUPABASE_URL =
  process.env.SUPABASE_URL ??
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://glyffnyhtrmdkuhfwcsv.supabase.co";

const SUPABASE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_PUBLISHABLE_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

type StationPayload = {
  name: string;
  city?: string;
  cnpj?: string;
  latitude?: number;
  longitude?: number;
  checkin_radius_meters?: number;
  active?: boolean;
};

function isValidCnpj(value: string) {
  return /^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/.test(value);
}

function validateStation(payload: StationPayload) {
  const errors: string[] = [];
  if (!payload.name?.trim()) errors.push("Nome do posto e obrigatorio");
  if (payload.cnpj && !isValidCnpj(payload.cnpj)) {
    errors.push("CNPJ deve estar no formato 00.000.000/0000-00");
  }
  if (payload.latitude !== undefined && (payload.latitude < -90 || payload.latitude > 90)) {
    errors.push("Latitude invalida");
  }
  if (payload.longitude !== undefined && (payload.longitude < -180 || payload.longitude > 180)) {
    errors.push("Longitude invalida");
  }
  return errors;
}

async function supabaseFetch(path: string, init?: RequestInit) {
  if (!SUPABASE_KEY) {
    return NextResponse.json(
      { error: "Supabase key nao configurada no servidor" },
      { status: 500 },
    );
  }

  const response = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    return NextResponse.json({ error: data }, { status: response.status });
  }
  return NextResponse.json(data);
}

export async function GET() {
  return supabaseFetch(
    "stations?select=id,name,city,cnpj,latitude,longitude,checkin_radius_meters,active&order=name.asc",
  );
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as StationPayload;
  const errors = validateStation(payload);
  if (errors.length) {
    return NextResponse.json({ errors }, { status: 400 });
  }

  return supabaseFetch("stations", {
    method: "POST",
    body: JSON.stringify({
      name: payload.name.trim(),
      city: payload.city?.trim() || "Pernambuco",
      cnpj: payload.cnpj?.trim() || null,
      latitude: payload.latitude ?? null,
      longitude: payload.longitude ?? null,
      checkin_radius_meters: payload.checkin_radius_meters ?? 300,
      active: payload.active ?? true,
    }),
  });
}

