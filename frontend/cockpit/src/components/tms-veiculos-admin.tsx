"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2Icon,
  PlusIcon,
  QrCodeIcon,
  RefreshCwIcon,
  TruckIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Compartment = {
  id: string;
  truck_id: string;
  compartment_number: number;
  capacity_liters: string | number;
  qr_code_identifier: string;
};

type Truck = {
  id: string;
  plate: string;
  model: string;
  status: "Ativo" | "Inativo";
  truck_compartments?: Compartment[];
};

type TruckForm = {
  plate: string;
  model: string;
  status: "Ativo" | "Inativo";
  compartment_capacities: string[];
};

const emptyForm: TruckForm = {
  plate: "",
  model: "",
  status: "Ativo",
  compartment_capacities: ["5000", "5000", "5000", "5000", "5000"],
};

const litersFormatter = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 0,
});

function cleanPlate(value: string) {
  return value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 7);
}

function maskPlate(value: string) {
  const clean = cleanPlate(value);
  if (clean.length <= 3) return clean;
  return `${clean.slice(0, 3)}-${clean.slice(3)}`;
}

function formatLiters(value: string | number) {
  return `${litersFormatter.format(Number(value) || 0)} L`;
}

function qrPreview(plate: string, number: number) {
  const clean = cleanPlate(plate);
  return clean ? `${clean}-COMP-${String(number).padStart(2, "0")}` : `PLACA-COMP-${String(number).padStart(2, "0")}`;
}

export function TmsVeiculosAdmin() {
  const [trucks, setTrucks] = useState<Truck[]>([]);
  const [form, setForm] = useState<TruckForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const totalCapacity = useMemo(
    () =>
      trucks.reduce(
        (sum, truck) =>
          sum +
          (truck.truck_compartments ?? []).reduce(
            (compartmentSum, compartment) => compartmentSum + Number(compartment.capacity_liters || 0),
            0,
          ),
        0,
      ),
    [trucks],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/tms/trucks", { cache: "no-store" });
      if (!response.ok) throw new Error("Falha ao carregar veiculos");
      setTrucks(await response.json());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao carregar veiculos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  function setCompartmentCapacity(index: number, value: string) {
    setForm((current) => ({
      ...current,
      compartment_capacities: current.compartment_capacities.map((capacity, capacityIndex) =>
        capacityIndex === index ? value.replace(/[^\d.]/g, "") : capacity,
      ),
    }));
  }

  async function save() {
    const capacities = form.compartment_capacities.map(Number);
    if (cleanPlate(form.plate).length !== 7) {
      toast.error("Informe uma placa com 7 caracteres");
      return;
    }
    if (capacities.some((capacity) => !Number.isFinite(capacity) || capacity <= 0)) {
      toast.error("Todos os compartimentos precisam ter capacidade maior que zero");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/tms/trucks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plate: form.plate,
          model: form.model,
          status: form.status,
          compartment_capacities: capacities,
        }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.errors?.join(", ") ?? body.error?.message ?? "Falha ao cadastrar veiculo");
      }

      setForm(emptyForm);
      toast.success("Veiculo cadastrado com 5 compartimentos");
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao salvar veiculo");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-[calc(100vh-3rem)] bg-background">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 md:px-8">
        <section className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <Badge variant="outline">Sprint 3 - Frota</Badge>
              <h1 className="mt-3 text-2xl font-semibold md:text-3xl">Veiculos e Compartimentos</h1>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                Cadastre caminhoes, defina os 5 compartimentos e gere os identificadores de QR Code para carregamento e descarga.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Kpi label="Veiculos" value={String(trucks.length)} />
              <Kpi label="Ativos" value={String(trucks.filter((truck) => truck.status === "Ativo").length)} />
              <Kpi label="Capacidade" value={formatLiters(totalCapacity)} />
            </div>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Novo veiculo</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField label="Placa" value={maskPlate(form.plate)} onChange={(plate) => setForm((old) => ({ ...old, plate: maskPlate(plate) }))} placeholder="ABC-1D23" />
              <FormField label="Modelo" value={form.model} onChange={(model) => setForm((old) => ({ ...old, model }))} placeholder="Volvo FH / Scania / Mercedes" />
              <label className="grid gap-2 text-sm">
                <span className="text-xs text-muted-foreground">Status</span>
                <select
                  className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/30"
                  value={form.status}
                  onChange={(event) => setForm((old) => ({ ...old, status: event.target.value as "Ativo" | "Inativo" }))}
                >
                  <option value="Ativo">Ativo</option>
                  <option value="Inativo">Inativo</option>
                </select>
              </label>

              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium">Compartimentos</p>
                  <p className="text-xs text-muted-foreground">Padrao do piloto: 5 compartimentos de 5.000 L.</p>
                </div>
                {form.compartment_capacities.map((capacity, index) => (
                  <div key={index} className="grid gap-2 rounded-xl border border-border/70 bg-background/50 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">C{index + 1}</span>
                      <span className="font-mono text-xs text-muted-foreground">{qrPreview(form.plate, index + 1)}</span>
                    </div>
                    <Input value={capacity} onChange={(event) => setCompartmentCapacity(index, event.target.value)} inputMode="decimal" />
                  </div>
                ))}
              </div>

              <Button className="w-full" onClick={save} disabled={saving || !form.model.trim()}>
                {saving ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
                Cadastrar veiculo
              </Button>
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>Frota cadastrada</CardTitle>
                <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                  <RefreshCwIcon className={loading ? "animate-spin" : ""} />
                  Atualizar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2Icon className="size-4 animate-spin" />
                  Carregando frota...
                </div>
              ) : trucks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border p-8 text-center">
                  <TruckIcon className="mx-auto size-8 text-muted-foreground" />
                  <p className="mt-3 font-medium">Nenhum veiculo cadastrado</p>
                </div>
              ) : (
                trucks.map((truck) => <TruckRow key={truck.id} truck={truck} />)
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}

function TruckRow({ truck }: { truck: Truck }) {
  const compartments = [...(truck.truck_compartments ?? [])].sort(
    (left, right) => left.compartment_number - right.compartment_number,
  );
  const capacity = compartments.reduce((sum, compartment) => sum + Number(compartment.capacity_liters || 0), 0);

  async function copyQr(value: string) {
    await navigator.clipboard.writeText(value);
    toast.success("QR Code copiado");
  }

  return (
    <article className="rounded-2xl border border-border/70 bg-background/45 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <TruckIcon className="size-4 text-muted-foreground" />
            <h3 className="font-semibold">{maskPlate(truck.plate)}</h3>
            <Badge variant={truck.status === "Ativo" ? "secondary" : "outline"}>{truck.status}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{truck.model}</p>
        </div>
        <div className="rounded-xl border border-border/70 bg-card px-3 py-2 text-sm">
          <span className="text-muted-foreground">Capacidade total </span>
          <span className="font-mono font-semibold">{formatLiters(capacity)}</span>
        </div>
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-5">
        {compartments.map((compartment) => (
          <button
            key={compartment.id}
            type="button"
            className="rounded-xl border border-border/70 bg-card p-3 text-left transition-colors hover:border-primary/50"
            onClick={() => void copyQr(compartment.qr_code_identifier)}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">C{compartment.compartment_number}</span>
              <QrCodeIcon className="size-4 text-muted-foreground" />
            </div>
            <p className="mt-2 font-mono text-sm">{formatLiters(compartment.capacity_liters)}</p>
            <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground">{compartment.qr_code_identifier}</p>
          </button>
        ))}
      </div>
    </article>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="grid gap-2 text-sm">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/55 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-xl font-semibold">{value}</p>
    </div>
  );
}
