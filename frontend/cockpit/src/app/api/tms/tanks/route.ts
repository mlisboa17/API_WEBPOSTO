import { NextRequest, NextResponse } from "next/server";

const SUPABASE_URL =
  process.env.SUPABASE_URL ??
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://glyffnyhtrmdkuhfwcsv.supabase.co";

const SUPABASE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_PUBLISHABLE_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

type TankPayload = {
  station_id: string;
  name: string;
  product_id: string;
  product_type: string;
  capacity_liters: number;
  current_stock_liters: number;
  qr_code_identifier?: string;
  active?: boolean;
};

function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .toUpperCase();
}

function validateTank(payload: TankPayload) {
  const errors: string[] = [];
  if (!payload.station_id) errors.push("Posto vinculado e obrigatorio");
  if (!payload.name?.trim()) errors.push("Identificacao fisica e obrigatoria");
  if (!payload.product_id) errors.push("Produto e obrigatorio");
  if (!payload.product_type?.trim()) errors.push("Tipo de produto e obrigatorio");
  if (!Number.isFinite(payload.capacity_liters) || payload.capacity_liters <= 0) {
    errors.push("Capacidade deve ser maior que zero");
  }
  if (!Number.isFinite(payload.current_stock_liters) || payload.current_stock_liters < 0) {
    errors.push("Estoque inicial nao pode ser negativo");
  }
  if (payload.current_stock_liters > payload.capacity_liters) {
    errors.push("Estoque inicial nao pode ser maior que a capacidade");
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

async function fetchStationName(stationId: string) {
  const response = await fetch(
    `${SUPABASE_URL}/rest/v1/stations?id=eq.${stationId}&select=name`,
    {
      headers: {
        apikey: SUPABASE_KEY ?? "",
        Authorization: `Bearer ${SUPABASE_KEY ?? ""}`,
      },
      cache: "no-store",
    },
  );
  const data = (await response.json()) as { name: string }[];
  return data[0]?.name ?? "POSTO";
}

export async function GET(request: NextRequest) {
  const stationId = request.nextUrl.searchParams.get("station_id");
  const filter = stationId ? `station_id=eq.${stationId}&` : "";

  return supabaseFetch(
    `tanks?${filter}select=id,station_id,name,product_id,product_type,capacity_liters,current_stock_liters,qr_code_identifier,active,tank_count,capacity_per_tank_liters,products(name,short_code),stations(name)&order=name.asc`,
  );
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as TankPayload;
  const errors = validateTank(payload);
  if (errors.length) {
    return NextResponse.json({ errors }, { status: 400 });
  }

  const stationName = await fetchStationName(payload.station_id);
  const qrCode =
    payload.qr_code_identifier?.trim() ||
    `${slugify(stationName)}-${slugify(payload.name)}-${slugify(payload.product_type)}`;

  return supabaseFetch("tanks", {
    method: "POST",
    body: JSON.stringify({
      station_id: payload.station_id,
      product_id: payload.product_id,
      name: payload.name.trim().toUpperCase(),
      product_type: payload.product_type.trim(),
      capacity_liters: payload.capacity_liters,
      current_stock_liters: payload.current_stock_liters,
      qr_code_identifier: qrCode,
      tank_count: 1,
      capacity_per_tank_liters: payload.capacity_liters,
      active: payload.active ?? true,
    }),
  });
}

