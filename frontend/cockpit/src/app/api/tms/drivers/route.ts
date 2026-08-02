import { NextRequest, NextResponse } from "next/server";

const SUPABASE_URL =
  process.env.SUPABASE_URL ??
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://glyffnyhtrmdkuhfwcsv.supabase.co";

const SUPABASE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_PUBLISHABLE_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

type DriverPayload = {
  name: string;
  cnh_number: string;
  cnh_expiration: string;
  mopp_certified: boolean;
  habitual_truck_id?: string | null;
  status?: "Ativo" | "Inativo";
};

function cleanCnh(value: string) {
  return value.replace(/\D/g, "").slice(0, 11);
}

function isExpired(date: string) {
  if (!date) return false;
  const today = new Date();
  const expiration = new Date(`${date}T00:00:00`);
  today.setHours(0, 0, 0, 0);
  return expiration < today;
}

function validateDriver(payload: DriverPayload) {
  const errors: string[] = [];
  const cnh = cleanCnh(payload.cnh_number ?? "");

  if (!payload.name?.trim()) errors.push("Nome do motorista e obrigatorio");
  if (cnh.length !== 11) errors.push("CNH deve conter 11 digitos");
  if (!payload.cnh_expiration) errors.push("Validade da CNH e obrigatoria");
  if (isExpired(payload.cnh_expiration)) {
    errors.push("CNH vencida. Por seguranca, o cadastro fica bloqueado ate regularizacao.");
  }

  return { errors, cnh };
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
  try {
    if (!SUPABASE_KEY) {
      return NextResponse.json(
        { error: "Supabase key nao configurada no servidor" },
        { status: 500 },
      );
    }

    const headers = {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
    };
    const [driversResponse, trucksResponse] = await Promise.all([
      fetch(
        `${SUPABASE_URL}/rest/v1/drivers?select=id,name,cnh_number,cnh_expiration,mopp_certified,habitual_truck_id,status&order=name.asc`,
        {
          headers,
          cache: "no-store",
        },
      ),
      fetch(`${SUPABASE_URL}/rest/v1/trucks?select=id,plate,model,status`, {
        headers,
        cache: "no-store",
      }),
    ]);

    const driversText = await driversResponse.text();
    const trucksText = await trucksResponse.text();
    const drivers = driversText ? JSON.parse(driversText) : [];
    const trucks = trucksText ? JSON.parse(trucksText) : [];

    if (!driversResponse.ok) return NextResponse.json({ error: drivers }, { status: driversResponse.status });
    if (!trucksResponse.ok) return NextResponse.json({ error: trucks }, { status: trucksResponse.status });

    const result = drivers.map((driver: { habitual_truck_id?: string | null }) => ({
      ...driver,
      trucks: trucks.find((truck: { id: string }) => truck.id === driver.habitual_truck_id) ?? null,
    }));

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Erro inesperado ao listar motoristas" },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as DriverPayload;
  const { errors, cnh } = validateDriver(payload);
  if (errors.length) {
    return NextResponse.json({ errors }, { status: 400 });
  }

  return supabaseFetch("drivers", {
    method: "POST",
    body: JSON.stringify({
      name: payload.name.trim(),
      cnh_number: cnh,
      cnh_expiration: payload.cnh_expiration,
      mopp_certified: Boolean(payload.mopp_certified),
      habitual_truck_id: payload.habitual_truck_id || null,
      status: payload.status ?? "Ativo",
    }),
  });
}
