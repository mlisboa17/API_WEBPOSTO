"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Calculator, Fuel, Package, RefreshCcw, ShoppingCart } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiService } from "@/lib/api";
import type { TankPrediction } from "@/types/api";
import { cn } from "@/lib/utils";

const CARRETA_L = 15000;

function brl(n: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n || 0);
}

function litrosFmt(n: number) {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(n || 0)} L`;
}

/** CPM ponderado após descarga: (estoque×cpm + lote×preço) / (estoque+lote) */
export function calcCpmPonderado(
  estoqueAtual: number,
  cpmAtual: number,
  volumePedido: number,
  precoDistribuidora: number
): number {
  const den = estoqueAtual + volumePedido;
  if (den <= 0) return precoDistribuidora || cpmAtual || 0;
  return (estoqueAtual * cpmAtual + volumePedido * precoDistribuidora) / den;
}

function sugestaoLitros(p: TankPrediction): number {
  if (p.sugestao_compra_litros > 0) return p.sugestao_compra_litros;
  // Cobertura para chegar a ~3 dias + buffer de 1 carreta mínima se crítico
  const target = Math.max(0, p.consumo_medio_diario * 3 - p.estoque_atual_litros);
  const espaco = Math.max(0, p.capacidade_tanque - p.estoque_atual_litros);
  const raw = Math.min(target > 0 ? target : CARRETA_L, espaco || CARRETA_L);
  return Math.round(raw / 1000) * 1000 || CARRETA_L;
}

export function PurchaseOrderAssistant({
  empresaCodigo,
  filialLabel,
}: {
  empresaCodigo?: number;
  filialLabel: string;
}) {
  const [items, setItems] = useState<TankPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState("");
  const [precoLote, setPrecoLote] = useState(5.8);
  const [volumeOverride, setVolumeOverride] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!empresaCodigo) {
      setItems([]);
      setMsg("Selecione uma filial para sugerir reposição.");
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await apiService.getInventoryPrediction(empresaCodigo, 3, 24);
      const list = (data.predicoes || []).filter(
        (p) => p.autonomia_dias_restantes < 3 || p.status_alerta !== "OK"
      );
      const source = list.length ? list : data.predicoes || [];
      setItems(source);
      setMsg(
        list.length
          ? null
          : "Nenhum tanque com autonomia < 3 dias — exibindo catálogo para simulação."
      );
      const first = source[0];
      if (first) {
        setSelectedKey(String(first.produto_codigo));
        const cpmAtual = first.cpm_rs_litro ?? 0;
        if (cpmAtual > 0) setPrecoLote(Number(cpmAtual.toFixed(3)));
      }
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Falha ao carregar previsão");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(
    () => items.find((p) => String(p.produto_codigo) === selectedKey) || items[0],
    [items, selectedKey]
  );

  const volumePedido = volumeOverride ?? (selected ? sugestaoLitros(selected) : CARRETA_L);
  const carretas = volumePedido / CARRETA_L;
  const cpmAtual = selected?.cpm_rs_litro || selected?.preco_venda_rs_litro || 0;
  const cpmNovo = selected
    ? calcCpmPonderado(
        selected.estoque_atual_litros,
        cpmAtual,
        volumePedido,
        precoLote
      )
    : 0;
  const deltaCpm = cpmNovo - cpmAtual;

  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <ShoppingCart size={18} className="text-emerald-400" />
              Assistente de Reposição & CPM
            </CardTitle>
            <CardDescription>
              Pedido sugerido para autonomia &lt; 3 dias • {filialLabel} • simule o CPM pós-descarga
            </CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
            <RefreshCcw size={14} className={cn("mr-1", loading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {msg ? <p className="text-xs text-amber-300">{msg}</p> : null}
        {!empresaCodigo ? (
          <p className="text-sm text-slate-300 py-6 text-center">
            Filtre uma filial (Casa Caiada, VIP ou Real) para gerar a sugestão de carreta.
          </p>
        ) : loading ? (
          <p className="text-sm text-slate-300 py-6 text-center">Calculando runway e pedido…</p>
        ) : !selected ? (
          <p className="text-sm text-slate-300 py-6 text-center">Sem tanques para esta filial.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="space-y-1.5">
                <span className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">
                  Combustível / Tanque
                </span>
                <select
                  className="w-full h-10 rounded-md border border-slate-700 bg-slate-950 text-slate-100 text-sm px-3"
                  value={String(selected.produto_codigo)}
                  onChange={(e) => {
                    setSelectedKey(e.target.value);
                    setVolumeOverride(null);
                  }}
                >
                  {items.map((p) => (
                    <option key={p.produto_codigo} value={p.produto_codigo}>
                      {p.produto_nome} — {p.autonomia_dias_restantes.toFixed(1)}d
                    </option>
                  ))}
                </select>
              </label>
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase text-slate-300 font-bold">Autonomia atual</p>
                  <p
                    className={cn(
                      "text-xl font-mono font-bold",
                      selected.autonomia_dias_restantes < 1.5
                        ? "text-rose-400"
                        : selected.autonomia_dias_restantes < 3
                          ? "text-amber-400"
                          : "text-emerald-400"
                    )}
                  >
                    {selected.autonomia_dias_restantes.toFixed(1)} dias
                  </p>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px]",
                    selected.autonomia_dias_restantes < 3
                      ? "border-amber-500/40 text-amber-300"
                      : "border-emerald-500/40 text-emerald-300"
                  )}
                >
                  {selected.alerta_label || selected.status_alerta}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                <p className="text-[10px] uppercase text-slate-300 font-bold flex items-center gap-1">
                  <Package size={12} /> Sugestão de pedido
                </p>
                <p className="text-2xl font-mono font-bold text-white mt-1">
                  {litrosFmt(volumePedido)}
                </p>
                <p className="text-xs text-sky-300 mt-1">
                  ≈ {carretas.toFixed(2)} carreta(s) de {litrosFmt(CARRETA_L)}
                </p>
                <div className="flex gap-1 mt-2">
                  {[10000, 15000, 30000].map((v) => (
                    <Button
                      key={v}
                      size="sm"
                      variant="outline"
                      className="text-[10px] h-7 px-2"
                      onClick={() => setVolumeOverride(v)}
                    >
                      {v / 1000}k L
                    </Button>
                  ))}
                </div>
              </div>

              <label className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 space-y-2">
                <span className="text-[10px] uppercase text-slate-300 font-bold flex items-center gap-1">
                  <Fuel size={12} /> Preço distribuidora (R$/L)
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={precoLote}
                  onChange={(e) => setPrecoLote(Number(e.target.value) || 0)}
                  className="w-full h-10 rounded-md border border-slate-700 bg-slate-900 text-white font-mono px-3"
                />
                <p className="text-[11px] text-slate-300">
                  CPM atual: {cpmAtual > 0 ? brl(cpmAtual) : "—"}/L
                </p>
              </label>

              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
                <p className="text-[10px] uppercase text-emerald-300 font-bold flex items-center gap-1">
                  <Calculator size={12} /> Novo CPM ponderado
                </p>
                <p className="text-2xl font-mono font-bold text-emerald-300 mt-1">
                  {brl(cpmNovo)}/L
                </p>
                <p
                  className={cn(
                    "text-xs mt-1 font-semibold",
                    deltaCpm > 0 ? "text-rose-400" : deltaCpm < 0 ? "text-emerald-400" : "text-slate-300"
                  )}
                >
                  {deltaCpm === 0
                    ? "Sem variação vs. CPM atual"
                    : `${deltaCpm > 0 ? "+" : ""}${deltaCpm.toFixed(4)} R$/L após descarga`}
                </p>
                <p className="text-[10px] text-slate-300 mt-2">
                  Estoque {litrosFmt(selected.estoque_atual_litros)} + lote {litrosFmt(volumePedido)}
                </p>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
