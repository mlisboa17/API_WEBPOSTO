"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Building2Icon,
  CheckCircle2Icon,
  Loader2Icon,
  MapPinIcon,
  PlusIcon,
  RefreshCwIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Station = {
  id: string;
  name: string;
  city?: string | null;
  cnpj?: string | null;
  latitude?: string | number | null;
  longitude?: string | number | null;
  checkin_radius_meters?: number | null;
  active: boolean;
};

const emptyForm = {
  name: "",
  city: "Pernambuco",
  cnpj: "",
  latitude: "",
  longitude: "",
  checkin_radius_meters: "300",
};

export function TmsPostosAdmin() {
  const [stations, setStations] = useState<Station[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const configuredCount = useMemo(
    () => stations.filter((station) => station.cnpj && station.latitude && station.longitude).length,
    [stations],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/tms/stations", { cache: "no-store" });
      if (!response.ok) throw new Error("Falha ao carregar postos");
      setStations(await response.json());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao carregar postos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function save() {
    setSaving(true);
    try {
      const response = await fetch("/api/tms/stations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          city: form.city,
          cnpj: form.cnpj || undefined,
          latitude: form.latitude ? Number(form.latitude) : undefined,
          longitude: form.longitude ? Number(form.longitude) : undefined,
          checkin_radius_meters: Number(form.checkin_radius_meters || 300),
        }),
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.errors?.join(", ") ?? "Falha ao cadastrar posto");
      }
      setForm(emptyForm);
      toast.success("Posto cadastrado");
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao salvar posto");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-[calc(100vh-3rem)] bg-background">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 md:px-8">
        <section className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <Badge variant="outline">Cadastro operacional</Badge>
              <h1 className="mt-3 text-2xl font-semibold md:text-3xl">Postos</h1>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                Cadastre novos postos com CNPJ e geolocalização para liberar check-in, descarga segura e leitura de estoque.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Kpi label="Postos ativos" value={String(stations.filter((item) => item.active).length)} />
              <Kpi label="Com CNPJ e geo" value={String(configuredCount)} />
              <Kpi label="Raio padrão" value="300m" />
            </div>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Novo posto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField label="Nome do posto" value={form.name} onChange={(name) => setForm((old) => ({ ...old, name }))} />
              <FormField label="Cidade" value={form.city} onChange={(city) => setForm((old) => ({ ...old, city }))} />
              <FormField label="CNPJ" value={form.cnpj} onChange={(cnpj) => setForm((old) => ({ ...old, cnpj }))} placeholder="00.000.000/0000-00" />
              <div className="grid gap-3 sm:grid-cols-2">
                <FormField label="Latitude" value={form.latitude} onChange={(latitude) => setForm((old) => ({ ...old, latitude }))} placeholder="-7.974487" />
                <FormField label="Longitude" value={form.longitude} onChange={(longitude) => setForm((old) => ({ ...old, longitude }))} placeholder="-34.834227" />
              </div>
              <FormField label="Raio check-in (m)" value={form.checkin_radius_meters} onChange={(checkin_radius_meters) => setForm((old) => ({ ...old, checkin_radius_meters }))} />
              <Button className="w-full" onClick={save} disabled={saving || !form.name.trim()}>
                {saving ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
                Cadastrar posto
              </Button>
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>Postos cadastrados</CardTitle>
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
                  Carregando postos...
                </div>
              ) : (
                stations.map((station) => <StationRow key={station.id} station={station} />)
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
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

function StationRow({ station }: { station: Station }) {
  const hasGeo = Boolean(station.latitude && station.longitude);
  return (
    <div className="grid gap-3 rounded-xl border border-border/70 bg-background/45 p-4 lg:grid-cols-[1fr_180px_170px] lg:items-center">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Building2Icon className="size-4 text-muted-foreground" />
          <p className="truncate font-medium">{station.name}</p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{station.city ?? "Cidade não informada"}</p>
      </div>
      <div className="text-sm">
        <p className="text-xs text-muted-foreground">CNPJ</p>
        <p className="font-mono">{station.cnpj ?? "pendente"}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={hasGeo ? "default" : "outline"}>
          {hasGeo ? <CheckCircle2Icon /> : <MapPinIcon />}
          {hasGeo ? "Geo OK" : "Sem geo"}
        </Badge>
        <Badge variant={station.active ? "secondary" : "outline"}>
          {station.active ? "Ativo" : "Inativo"}
        </Badge>
      </div>
    </div>
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
