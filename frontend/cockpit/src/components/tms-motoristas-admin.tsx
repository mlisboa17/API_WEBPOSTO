"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangleIcon,
  BadgeCheckIcon,
  CheckCircle2Icon,
  IdCardIcon,
  Loader2Icon,
  PlusIcon,
  RefreshCwIcon,
  UserRoundIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Truck = {
  id: string;
  plate: string;
  model: string;
  status: "Ativo" | "Inativo";
};

type Driver = {
  id: string;
  name: string;
  cnh_number: string;
  cnh_expiration: string;
  mopp_certified: boolean;
  habitual_truck_id?: string | null;
  status: "Ativo" | "Inativo";
  trucks?: { id: string; plate: string; model: string } | null;
};

type DriverForm = {
  name: string;
  cnh_number: string;
  cnh_expiration: string;
  mopp_certified: boolean;
  habitual_truck_id: string;
  status: "Ativo" | "Inativo";
};

const emptyForm: DriverForm = {
  name: "",
  cnh_number: "",
  cnh_expiration: "",
  mopp_certified: true,
  habitual_truck_id: "",
  status: "Ativo",
};

function cleanCnh(value: string) {
  return value.replace(/\D/g, "").slice(0, 11);
}

function maskCnh(value: string) {
  return cleanCnh(value);
}

function maskPlate(value: string) {
  const clean = value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 7);
  if (clean.length <= 3) return clean;
  return `${clean.slice(0, 3)}-${clean.slice(3)}`;
}

function isExpired(date: string) {
  if (!date) return false;
  const today = new Date();
  const expiration = new Date(`${date}T00:00:00`);
  today.setHours(0, 0, 0, 0);
  return expiration < today;
}

function daysToExpire(date: string) {
  if (!date) return null;
  const today = new Date();
  const expiration = new Date(`${date}T00:00:00`);
  today.setHours(0, 0, 0, 0);
  return Math.ceil((expiration.getTime() - today.getTime()) / 86_400_000);
}

export function TmsMotoristasAdmin() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [trucks, setTrucks] = useState<Truck[]>([]);
  const [form, setForm] = useState<DriverForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const activeDrivers = useMemo(
    () => drivers.filter((driver) => driver.status === "Ativo").length,
    [drivers],
  );
  const expiringDrivers = useMemo(
    () => drivers.filter((driver) => {
      const days = daysToExpire(driver.cnh_expiration);
      return days !== null && days >= 0 && days <= 30;
    }).length,
    [drivers],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [driversResponse, trucksResponse] = await Promise.all([
        fetch("/api/tms/drivers", { cache: "no-store" }),
        fetch("/api/tms/trucks", { cache: "no-store" }),
      ]);
      if (!driversResponse.ok) throw new Error("Falha ao carregar motoristas");
      if (!trucksResponse.ok) throw new Error("Falha ao carregar veiculos");
      setDrivers(await driversResponse.json());
      setTrucks(await trucksResponse.json());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao carregar cadastros");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function save() {
    if (cleanCnh(form.cnh_number).length !== 11) {
      toast.error("CNH deve conter 11 digitos");
      return;
    }
    if (isExpired(form.cnh_expiration)) {
      toast.error("CNH vencida. Cadastro bloqueado por regra de seguranca.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/tms/drivers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          cnh_number: cleanCnh(form.cnh_number),
          habitual_truck_id: form.habitual_truck_id || null,
        }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.errors?.join(", ") ?? body.error?.message ?? "Falha ao cadastrar motorista");
      }

      setForm(emptyForm);
      toast.success("Motorista cadastrado");
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao salvar motorista");
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
              <Badge variant="outline">Sprint 3 - Motoristas</Badge>
              <h1 className="mt-3 text-2xl font-semibold md:text-3xl">Motoristas</h1>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                Controle CNH, MOPP e caminhao habitual para reduzir risco operacional antes da programacao de carga.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Kpi label="Motoristas" value={String(drivers.length)} />
              <Kpi label="Ativos" value={String(activeDrivers)} />
              <Kpi label="CNH ate 30 dias" value={String(expiringDrivers)} />
            </div>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Novo motorista</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField label="Nome" value={form.name} onChange={(name) => setForm((old) => ({ ...old, name }))} placeholder="Nome completo" />
              <FormField label="CNH" value={maskCnh(form.cnh_number)} onChange={(cnh_number) => setForm((old) => ({ ...old, cnh_number: maskCnh(cnh_number) }))} placeholder="11 digitos" inputMode="numeric" />
              <FormField label="Validade CNH" value={form.cnh_expiration} onChange={(cnh_expiration) => setForm((old) => ({ ...old, cnh_expiration }))} type="date" />
              {isExpired(form.cnh_expiration) ? (
                <div className="flex items-start gap-2 rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-900 dark:text-red-200">
                  <AlertTriangleIcon className="mt-0.5 size-4" />
                  CNH vencida. O sistema bloqueia o cadastro para evitar programacao irregular.
                </div>
              ) : null}
              <label className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-background/50 p-3 text-sm">
                <span>
                  <span className="font-medium">MOPP ativo</span>
                  <span className="block text-xs text-muted-foreground">Obrigatorio para transporte de combustiveis.</span>
                </span>
                <input
                  type="checkbox"
                  className="size-5 accent-primary"
                  checked={form.mopp_certified}
                  onChange={(event) => setForm((old) => ({ ...old, mopp_certified: event.target.checked }))}
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span className="text-xs text-muted-foreground">Caminhao habitual</span>
                <select
                  className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/30"
                  value={form.habitual_truck_id}
                  onChange={(event) => setForm((old) => ({ ...old, habitual_truck_id: event.target.value }))}
                >
                  <option value="">Sem vinculo fixo</option>
                  {trucks.map((truck) => (
                    <option key={truck.id} value={truck.id}>
                      {maskPlate(truck.plate)} - {truck.model}
                    </option>
                  ))}
                </select>
              </label>
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
              <Button className="w-full" onClick={save} disabled={saving || !form.name.trim()}>
                {saving ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
                Cadastrar motorista
              </Button>
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>Motoristas cadastrados</CardTitle>
                <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                  <RefreshCwIcon className={loading ? "animate-spin" : ""} />
                  Atualizar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2Icon className="size-4 animate-spin" />
                  Carregando motoristas...
                </div>
              ) : drivers.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border p-8 text-center">
                  <UserRoundIcon className="mx-auto size-8 text-muted-foreground" />
                  <p className="mt-3 font-medium">Nenhum motorista cadastrado</p>
                </div>
              ) : (
                drivers.map((driver) => <DriverRow key={driver.id} driver={driver} />)
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}

function DriverRow({ driver }: { driver: Driver }) {
  const days = daysToExpire(driver.cnh_expiration);
  const expired = isExpired(driver.cnh_expiration);
  const warning = days !== null && days >= 0 && days <= 30;

  return (
    <article className="grid gap-3 rounded-2xl border border-border/70 bg-background/45 p-4 lg:grid-cols-[1fr_180px_180px_160px] lg:items-center">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <UserRoundIcon className="size-4 text-muted-foreground" />
          <p className="truncate font-medium">{driver.name}</p>
          <Badge variant={driver.status === "Ativo" ? "secondary" : "outline"}>{driver.status}</Badge>
        </div>
        <p className="mt-1 flex items-center gap-1 font-mono text-xs text-muted-foreground">
          <IdCardIcon className="size-3" />
          {driver.cnh_number}
        </p>
      </div>
      <div className="text-sm">
        <p className="text-xs text-muted-foreground">CNH</p>
        <p className={expired ? "font-medium text-red-600" : warning ? "font-medium text-amber-600" : "font-medium"}>
          {driver.cnh_expiration}
        </p>
      </div>
      <div className="text-sm">
        <p className="text-xs text-muted-foreground">Caminhao habitual</p>
        <p className="font-medium">{driver.trucks ? maskPlate(driver.trucks.plate) : "Sem vinculo"}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge variant={driver.mopp_certified ? "default" : "destructive"}>
          {driver.mopp_certified ? <BadgeCheckIcon /> : <AlertTriangleIcon />}
          MOPP
        </Badge>
        <Badge variant={expired ? "destructive" : warning ? "outline" : "secondary"}>
          {expired || warning ? <AlertTriangleIcon /> : <CheckCircle2Icon />}
          {expired ? "Vencida" : warning ? "A vencer" : "CNH OK"}
        </Badge>
      </div>
    </article>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  inputMode,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  inputMode?: "text" | "numeric" | "decimal";
}) {
  return (
    <label className="grid gap-2 text-sm">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        inputMode={inputMode}
      />
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
