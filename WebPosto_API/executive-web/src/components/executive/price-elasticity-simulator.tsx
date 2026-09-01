"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Calculator, Fuel, RefreshCcw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiService } from "@/lib/api";
import { cn } from "@/lib/utils";

type Product = {
  codigoProduto: string;
  nomeProduto: string;
  empresaCodigo: number;
  empresaNome: string;
  label: string;
  litros: number;
  precoMedioRsLitro: number;
  custoMedioRsLitro: number;
  coeficienteElasticidade: number;
};

type Projection = {
  volumeBaseLitros: number;
  volumeNovoLitros: number;
  deltaVolumePct: number;
  faturamentoBase: number;
  faturamentoNovo: number;
  lucroBrutoBase: number;
  lucroBrutoNovo: number;
  precoBase: number;
  precoNovo: number;
};

function brl(n: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n || 0);
}

function litrosFmt(n: number) {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(n || 0)} L`;
}

export function PriceElasticitySimulator({
  empresaCodigo,
  filialLabel,
}: {
  empresaCodigo?: number;
  filialLabel: string;
}) {
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState("");
  const [delta, setDelta] = useState(0);
  const [epsilon, setEpsilon] = useState(-1.2);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [projection, setProjection] = useState<Projection | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getElasticityProducts(empresaCodigo, 90);
      const list = (data.produtos || []) as Product[];
      setProducts(list);
      setMsg(data.mensagem || null);
      if (list.length) {
        const key = `${list[0].empresaCodigo}:${list[0].codigoProduto}`;
        setSelected(key);
        setEpsilon(list[0].coeficienteElasticidade || -1.2);
      } else {
        setSelected("");
        setProjection(null);
      }
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Falha ao carregar histórico");
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo]);

  useEffect(() => {
    void load();
  }, [load]);

  const currentProduct = useMemo(() => {
    const [emp, code] = selected.split(":");
    return products.find(
      (p) => String(p.empresaCodigo) === emp && String(p.codigoProduto) === code
    );
  }, [products, selected]);

  const localProjection = useMemo(() => {
    if (!currentProduct || currentProduct.litros <= 0 || currentProduct.precoMedioRsLitro <= 0) {
      return null;
    }
    const precoBase = currentProduct.precoMedioRsLitro;
    const litrosBase = currentProduct.litros;
    const custo = currentProduct.custoMedioRsLitro || precoBase * 0.88;
    const eps = epsilon || currentProduct.coeficienteElasticidade || -1.2;
    const deltaPctPreco = delta / precoBase;
    const deltaPctVol = eps * deltaPctPreco;
    const litrosNovo = Math.max(0, litrosBase * (1 + deltaPctVol));
    const precoNovo = Math.max(0.01, precoBase + delta);
    return {
      volumeBaseLitros: litrosBase,
      volumeNovoLitros: litrosNovo,
      deltaVolumePct: deltaPctVol * 100,
      faturamentoBase: litrosBase * precoBase,
      faturamentoNovo: litrosNovo * precoNovo,
      lucroBrutoBase: litrosBase * Math.max(precoBase - custo, 0),
      lucroBrutoNovo: litrosNovo * Math.max(precoNovo - custo, 0),
      precoBase,
      precoNovo,
    } satisfies Projection;
  }, [currentProduct, delta, epsilon]);

  useEffect(() => {
    setProjection(localProjection);
  }, [localProjection]);

  useEffect(() => {
    if (currentProduct) {
      setEpsilon(currentProduct.coeficienteElasticidade || -1.2);
    }
  }, [currentProduct]);

  const syncApi = async () => {
    if (!currentProduct) return;
    const data = await apiService.simulateElasticity(
      currentProduct.empresaCodigo,
      currentProduct.codigoProduto,
      delta,
      90
    );
    if (data.projecao) setProjection(data.projecao as Projection);
  };

  return (
    <Card className="border-cyan-500/20 bg-slate-900/90">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Calculator className="text-cyan-400" size={18} />
              Simulador de Elasticidade de Preço
            </CardTitle>
            <CardDescription>
              Histórico local 90 dias • {filialLabel} • Δ% Volume = ε × Δ% Preço
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void load()}
            disabled={loading}
            className="border-cyan-500/30 text-cyan-300"
          >
            <RefreshCcw size={14} className={cn(loading && "animate-spin")} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {msg && products.length === 0 ? (
          <p className="text-sm text-amber-300/90 py-6 text-center">{msg}</p>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <label className="block space-y-1.5">
                <span className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
                  Combustível / Filial
                </span>
                <select
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                  className="w-full rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                >
                  {products.map((p) => (
                    <option
                      key={`${p.empresaCodigo}-${p.codigoProduto}`}
                      value={`${p.empresaCodigo}:${p.codigoProduto}`}
                    >
                      {p.label || `${p.nomeProduto} — ${p.empresaNome}`}
                    </option>
                  ))}
                </select>
              </label>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
                    Variação de preço (R$/L)
                  </span>
                  <Badge variant="outline" className="border-white/10 text-cyan-300 font-mono">
                    {delta >= 0 ? "+" : ""}
                    {delta.toFixed(2)}
                  </Badge>
                </div>
                <input
                  type="range"
                  min={-0.5}
                  max={0.5}
                  step={0.02}
                  value={delta}
                  onChange={(e) => setDelta(Number(e.target.value))}
                  onMouseUp={() => void syncApi()}
                  onTouchEnd={() => void syncApi()}
                  className="w-full accent-cyan-400"
                />
                <div className="flex justify-between text-[10px] text-slate-300">
                  <span>-R$ 0,50</span>
                  <span className="flex items-center gap-1">
                    <Fuel size={10} /> ε = {epsilon.toFixed(2)}
                  </span>
                  <span>+R$ 0,50</span>
                </div>
              </div>
            </div>

            {projection ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <ProjCard
                  label="Novo Volume"
                  value={litrosFmt(projection.volumeNovoLitros)}
                  delta={`${projection.deltaVolumePct >= 0 ? "+" : ""}${projection.deltaVolumePct.toFixed(1)}%`}
                  good={projection.volumeNovoLitros >= projection.volumeBaseLitros}
                />
                <ProjCard
                  label="Novo Faturamento"
                  value={brl(projection.faturamentoNovo)}
                  delta={brl(projection.faturamentoNovo - projection.faturamentoBase)}
                  good={projection.faturamentoNovo >= projection.faturamentoBase}
                />
                <ProjCard
                  label="Lucro Bruto Projetado"
                  value={brl(projection.lucroBrutoNovo)}
                  delta={brl(projection.lucroBrutoNovo - projection.lucroBrutoBase)}
                  good={projection.lucroBrutoNovo >= projection.lucroBrutoBase}
                />
              </div>
            ) : null}

            {currentProduct ? (
              <p className="text-[11px] text-slate-300">
                Base 90d: {litrosFmt(currentProduct.litros)} @{" "}
                {brl(currentProduct.precoMedioRsLitro)}/L → preço simulado{" "}
                {brl((currentProduct.precoMedioRsLitro || 0) + delta)}/L
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ProjCard({
  label,
  value,
  delta,
  good,
}: {
  label: string;
  value: string;
  delta: string;
  good: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-white/[0.03] p-3">
      <p className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">{label}</p>
      <p className="text-xl font-bold font-mono text-white mt-1">{value}</p>
      <p className={cn("text-xs mt-1 font-semibold", good ? "text-emerald-300" : "text-rose-300")}>
        {delta}
      </p>
    </div>
  );
}
