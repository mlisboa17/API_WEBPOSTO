import { NextRequest, NextResponse } from "next/server";

const SUPABASE_URL =
  process.env.SUPABASE_URL ??
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://glyffnyhtrmdkuhfwcsv.supabase.co";

const SUPABASE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY ??
  process.env.SUPABASE_PUBLISHABLE_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

type TruckPayload = {
  plate: string;
  model: string;
  status?: "Ativo" | "Inativo";
  compartment_capacities: number[];
};

function cleanPlate(value: string) {
  return value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 7);
}

function validateTruck(payload: TruckPayload) {
  const errors: string[] = [];
  const plate = cleanPlate(payload.plate ?? "");

  if (plate.length !== 7) errors.push("Placa deve ter 7 caracteres");
  if (!payload.model?.trim()) errors.push("Modelo do caminhao e obrigatorio");
  if (!Array.isArray(payload.compartment_capacities) || payload.compartment_capacities.length !== 5) {
    errors.push("Informe a capacidade dos 5 compartimentos");
  }
  payload.compartment_capacities?.forEach((capacity, index) => {
    if (!Number.isFinite(capacity) || capacity <= 0) {
      errors.push(`Capacidade invalida no compartimento ${index + 1}`);
    }
  });

  return { errors, plate };
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
    const [trucksResponse, compartmentsResponse] = await Promise.all([
      fetch(`${SUPABASE_URL}/rest/v1/trucks?select=id,plate,model,status,created_at&order=plate.asc`, {
        headers,
        cache: "no-store",
      }),
      fetch(
        `${SUPABASE_URL}/rest/v1/truck_compartments?select=id,truck_id,compartment_number,capacity_liters,qr_code_identifier&order=compartment_number.asc`,
        {
          headers,
          cache: "no-store",
        },
      ),
    ]);

    const trucksText = await trucksResponse.text();
    const compartmentsText = await compartmentsResponse.text();
    const trucks = trucksText ? JSON.parse(trucksText) : [];
    const compartments = compartmentsText ? JSON.parse(compartmentsText) : [];

    if (!trucksResponse.ok) return NextResponse.json({ error: trucks }, { status: trucksResponse.status });
    if (!compartmentsResponse.ok) {
      return NextResponse.json({ error: compartments }, { status: compartmentsResponse.status });
    }

    const result = trucks.map((truck: { id: string }) => ({
      ...truck,
      truck_compartments: compartments.filter(
        (compartment: { truck_id: string }) => compartment.truck_id === truck.id,
      ),
    }));

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Erro inesperado ao listar veiculos" },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as TruckPayload;
  const { errors, plate } = validateTruck(payload);
  if (errors.length) {
    return NextResponse.json({ errors }, { status: 400 });
  }

  return supabaseFetch("rpc/create_truck_with_compartments", {
    method: "POST",
    body: JSON.stringify({
      p_plate: plate,
      p_model: payload.model.trim(),
      p_status: payload.status ?? "Ativo",
      p_compartment_capacities: payload.compartment_capacities,
    }),
  });
}
