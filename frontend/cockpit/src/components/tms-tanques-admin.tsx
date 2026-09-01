"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2Icon,
  CopyIcon,
  DatabaseIcon,
  GaugeIcon,
  Loader2Icon,
  PlusIcon,
  QrCodeIcon,
  RefreshCwIcon,
  XIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Station = {
  id: string;
  name: string;
  cnpj?: string | null;
  latitude?: string | number | null;
  longitude?: string | number | null;
  active: boolean;
};

type Product = {
  id: string;
  name: string;
  short_code?: string | null;
};

type Tank = {
  id: string;
  station_id: string;
  name?: string | null;
  product_id?: string | null;
  product_type?: string | null;
  capacity_liters?: string | number | null;
  current_stock_liters?: string | number | null;
  qr_code_identifier?: string | null;
  active: boolean;
  products?: { name?: string | null; short_code?: string | null } | null;
  stations?: { name?: string | null } | null;
};

type TankForm = {
  station_id: string;
  name: string;
  product_id: string;
  capacity_liters: string;
  current_stock_liters: string;
};

const emptyForm: TankForm = {
  station_id: "",
  name: "",
  product_id: "",
  capacity_liters: "15000",
  current_stock_liters: "",
};

const litersFormatter = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 0,
});

function toNumber(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return 0;
  return Number(value);
}

function formatLiters(value: string | number | null | undefined) {
  return `${litersFormatter.format(toNumber(value))} L`;
}

function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .toUpperCase();
}

function getOccupancy(tank: Tank) {
  const capacity = toNumber(tank.capacity_liters);
  const stock = toNumber(tank.current_stock_liters);
  if (capacity <= 0) return 0;
  return Math.min(100, Math.max(0, (stock / capacity) * 100));
}

function occupancyTone(percent: number) {
  if (percent >= 60) return "bg-emerald-500";
  if (percent >= 25) return "bg-amber-500";
  return "bg-red-500";
}

export function TmsTanquesAdmin() {
  const [stations, setStations] = useState<Station[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [tanks, setTanks] = useState<Tank[]>([]);
  const [selectedStationId, setSelectedStationId] = useState("");
  const [form, setForm] = useState<TankForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const selectedStation = useMemo(
    () => stations.find((station) => station.id === selectedStationId),
    [stations, selectedStationId],
  );
  const selectedProduct = useMemo(
    () => products.find((product) => product.id === form.product_id),
    [form.product_id, products],
  );
  const totalCapacity = useMemo(
    () => tanks.reduce((sum, tank) => sum + toNumber(tank.capacity_liters), 0),
    [tanks],
  );
  const totalStock = useMemo(
    () => tanks.reduce((sum, tank) => sum + toNumber(tank.current_stock_liters), 0),
    [tanks],
  );
  const occupancy = totalCapacity > 0 ? (totalStock / totalCapacity) * 100 : 0;
  const qrPreview = useMemo(() => {
    const stationName = stations.find((station) => station.id === form.station_id)?.name ?? "";
    const productName = selectedProduct?.name ?? "";
    if (!stationName || !form.name || !productName) return "";
    return `${slugify(stationName)}-${slugify(form.name)}-${slugify(productName)}`;
  }, [form.name, form.station_id, selectedProduct?.name, stations]);

  const loadStationsAndProducts = useCallback(async () => {
    const [stationsResponse, productsResponse] = await Promise.all([
      fetch("/api/tms/stations", { cache: "no-store" }),
      fetch("/api/tms/products", { cache: "no-store" }),
    ]);

    if (!stationsResponse.ok) throw new Error("Falha ao carregar postos");
    if (!productsResponse.ok) throw new Error("Falha ao carregar produtos");

    const stationsData = (await stationsResponse.json()) as Station[];
    const productsData = (await productsResponse.json()) as Product[];
    setStations(stationsData);
    setProducts(productsData);
    setSelectedStationId((current) => current || stationsData[0]?.id || "");
    setForm((current) => ({
      ...current,
      station_id: current.station_id || stationsData[0]?.id || "",
      product_id: current.product_id || productsData[0]?.id || "",
    }));
  }, []);

  const loadTanks = useCallback(async (stationId: string) => {
    if (!stationId) {
      setTanks([]);
      return;
    }

    const response = await fetch(`/api/tms/tanks?station_id=${stationId}`, {
      cache: "no-store",
    });
    if (!response.ok) throw new Error("Falha ao carregar tanques");
    setTanks(await response.json());
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      await loadStationsAndProducts();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, [loadStationsAndProducts]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedStationId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    loadTanks(selectedStationId)
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "Erro ao carregar tanques");
      })
      .finally(() => setLoading(false));
  }, [loadTanks, selectedStationId]);

  function openCreateModal() {
    const nextNumber = String(tanks.length + 1).padStart(2, "0");
    setForm((current) => ({
      ...current,
      station_id: selectedStationId,
      name: current.name || `TQ-${nextNumber}`,
      product_id: current.product_id || products[0]?.id || "",
      capacity_liters: current.capacity_liters || "15000",
      current_stock_liters: current.current_stock_liters || "",
    }));
    setModalOpen(true);
  }

  async function save() {
    const capacity = Number(form.capacity_liters);
    const stock = Number(form.current_stock_liters);
    if (stock > capacity) {
      toast.error("Estoque inicial nao pode ser maior que a capacidade");
      return;
    }
    if (!selectedProduct) {
      toast.error("Selecione um produto");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/tms/tanks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          station_id: form.station_id,
          name: form.name,
          product_id: form.product_id,
          product_type: selectedProduct.name,
          capacity_liters: capacity,
          current_stock_liters: stock,
          qr_code_identifier: qrPreview,
        }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.errors?.join(", ") ?? "Falha ao cadastrar tanque");
      }

      toast.success("Tanque cadastrado");
      setModalOpen(false);
      setForm((current) => ({ ...emptyForm, station_id: current.station_id, product_id: current.product_id }));
      await loadTanks(selectedStationId);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao salvar tanque");
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
              <Badge variant="outline">Cadastro operacional</Badge>
              <h1 className="mt-3 text-2xl font-semibold md:text-3xl">Tanques dos Postos</h1>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                Vincule tanques aos postos, controle estoque inicial e gere o identificador de QR Code usado na descarga segura.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Kpi label="Tanques" value={String(tanks.length)} />
              <Kpi label="Capacidade" value={formatLiters(totalCapacity)} />
              <Kpi label="Ocupacao" value={`${occupancy.toFixed(0)}%`} />
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-border/70 bg-card p-4 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <label className="grid gap-2 text-sm lg:min-w-[360px]">
              <span className="text-xs text-muted-foreground">Posto</span>
              <select
                className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/30"
                value={selectedStationId}
                onChange={(event) => {
                  setSelectedStationId(event.target.value);
                  setForm((current) => ({ ...current, station_id: event.target.value }));
                }}
              >
                {stations.map((station) => (
                  <option key={station.id} value={station.id}>
                    {station.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void loadTanks(selectedStationId)} disabled={loading}>
                <RefreshCwIcon className={loading ? "animate-spin" : ""} />
                Atualizar
              </Button>
              <Button onClick={openCreateModal} disabled={!selectedStationId || products.length === 0}>
                <PlusIcon />
                Novo tanque
              </Button>
            </div>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
          <section className="grid gap-4 lg:grid-cols-2">
            {loading ? (
              <div className="col-span-full flex items-center gap-2 rounded-2xl border border-border/70 bg-card p-5 text-sm text-muted-foreground">
                <Loader2Icon className="size-4 animate-spin" />
                Carregando tanques...
              </div>
            ) : tanks.length === 0 ? (
              <div className="col-span-full rounded-2xl border border-dashed border-border bg-card p-8 text-center">
                <DatabaseIcon className="mx-auto size-8 text-muted-foreground" />
                <p className="mt-3 font-medium">Nenhum tanque cadastrado para este posto</p>
                <p className="mt-1 text-sm text-muted-foreground">Cadastre os tanques físicos e cole o QR Code no tanque correspondente.</p>
              </div>
            ) : (
              tanks.map((tank) => <TankCard key={tank.id} tank={tank} />)
            )}
          </section>

          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Resumo do posto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs text-muted-foreground">Posto selecionado</p>
                <p className="mt-1 font-medium">{selectedStation?.name ?? "Selecione um posto"}</p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{selectedStation?.cnpj ?? "CNPJ pendente"}</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-background/50 p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Estoque total</span>
                  <span className="font-mono font-semibold">{formatLiters(totalStock)}</span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, occupancy)}%` }} />
                </div>
              </div>
              <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-4 text-sm text-amber-900 dark:text-amber-200">
                O QR Code do tanque deve ser fixado fisicamente no bocal/tampa do tanque correto para bloquear descarga em produto errado.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {modalOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-background/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl border border-border bg-card p-5 shadow-xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Badge variant="outline">Novo tanque</Badge>
                <h2 className="mt-2 text-xl font-semibold">Cadastrar tanque do posto</h2>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setModalOpen(false)} aria-label="Fechar">
                <XIcon />
              </Button>
            </div>

            <div className="mt-5 grid gap-4">
              <label className="grid gap-2 text-sm">
                <span className="text-xs text-muted-foreground">Posto vinculado</span>
                <select
                  className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/30"
                  value={form.station_id}
                  onChange={(event) => setForm((current) => ({ ...current, station_id: event.target.value }))}
                >
                  {stations.map((station) => (
                    <option key={station.id} value={station.id}>
                      {station.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <FormField label="Identificacao fisica" value={form.name} onChange={(name) => setForm((old) => ({ ...old, name }))} placeholder="TQ-01" />
                <label className="grid gap-2 text-sm">
                  <span className="text-xs text-muted-foreground">Produto</span>
                  <select
                    className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/30"
                    value={form.product_id}
                    onChange={(event) => setForm((current) => ({ ...current, product_id: event.target.value }))}
                  >
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <FormField label="Capacidade (litros)" value={form.capacity_liters} onChange={(capacity_liters) => setForm((old) => ({ ...old, capacity_liters }))} inputMode="decimal" />
                <FormField label="Estoque inicial (litros)" value={form.current_stock_liters} onChange={(current_stock_liters) => setForm((old) => ({ ...old, current_stock_liters }))} inputMode="decimal" />
              </div>
              <div className="rounded-xl border border-border/70 bg-background/60 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <QrCodeIcon className="size-4 text-muted-foreground" />
                  Texto do QR Code
                </div>
                <p className="mt-2 break-all font-mono text-sm text-muted-foreground">{qrPreview || "Preencha posto, tanque e produto"}</p>
              </div>
              <Button onClick={save} disabled={saving || !form.station_id || !form.name || !form.product_id}>
                {saving ? <Loader2Icon className="animate-spin" /> : <CheckCircle2Icon />}
                Salvar tanque
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function TankCard({ tank }: { tank: Tank }) {
  const productName = tank.product_type ?? tank.products?.name ?? "Produto pendente";
  const percent = getOccupancy(tank);
  const qrCode = tank.qr_code_identifier ?? "QR pendente";

  async function copyQr() {
    await navigator.clipboard.writeText(qrCode);
    toast.success("QR Code copiado");
  }

  return (
    <article className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm transition-colors hover:border-primary/40">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GaugeIcon className="size-4 text-muted-foreground" />
            <h3 className="font-semibold">{tank.name ?? "Tanque sem identificacao"}</h3>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{productName}</p>
        </div>
        <Badge variant={tank.active ? "secondary" : "outline"}>{tank.active ? "Ativo" : "Inativo"}</Badge>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Metric label="Estoque atual" value={formatLiters(tank.current_stock_liters)} />
        <Metric label="Capacidade" value={formatLiters(tank.capacity_liters)} />
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Ocupacao</span>
          <span className="font-mono font-semibold">{percent.toFixed(0)}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-muted">
          <div className={`h-full rounded-full ${occupancyTone(percent)}`} style={{ width: `${percent}%` }} />
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-border/70 bg-background/55 p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">QR Code</p>
            <p className="mt-1 truncate font-mono text-xs">{qrCode}</p>
          </div>
          <Button variant="outline" size="icon" onClick={copyQr} aria-label="Copiar QR Code">
            <CopyIcon />
          </Button>
        </div>
      </div>
    </article>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
  inputMode = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
}) {
  return (
    <label className="grid gap-2 text-sm">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} inputMode={inputMode} />
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/45 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono font-semibold">{value}</p>
    </div>
  );
}
