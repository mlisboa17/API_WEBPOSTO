"use client";

import { useEffect, useState } from "react";
import { TrendingUp, Droplet, Wallet, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  fetchPresidentDashboard,
  formatLitros,
  hojeLocalIso,
  type TotaisDiaPista,
} from "@/services/webposto/pista";
import { apiService } from "@/lib/api";

export interface PresidentTopKpisProps {
  totais: TotaisDiaPista | null;
  alertasCriticos: number;
  loading?: boolean;
  fromCache?: boolean;
}

function formatBRL(val: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val || 0);
}

export function PresidentTopKpis({
  totais,
  alertasCriticos,
  loading = false,
  fromCache = false,
}: PresidentTopKpisProps) {
  const fat = totais?.faturamentoTotal ?? 0;
  const litros = totais?.volumetriaTotalLitros ?? 0;
  const pvm = totais?.pvmMedio ?? (litros > 0 ? fat / litros : 0);
  const vacuoCartoes = totais?.valorCartoesDia ?? 0;
  const qtdCartoes = totais?.qtdCartoesDia ?? 0;
  const qtd = totais?.qtdTotalAbastecimentos ?? 0;
  const criticos = alertasCriticos || totais?.alertasCriticosRetencao || 0;

  const cards = [
    {
      title: "Faturamento Real do Dia",
      value: formatBRL(fat),
      sub: `${qtd.toLocaleString("pt-BR")} abast. · PVM ${formatBRL(pvm)}/L`,
      icon: <TrendingUp className="text-emerald-400" size={18} />,
      accent: "border-emerald-500/30",
      badge: "DIA COMPLETO",
    },
    {
      title: "Volumetria & PVM",
      value: formatLitros(litros),
      sub: `PVM médio ${formatBRL(pvm)}/L · margem unitária de venda`,
      icon: <Droplet className="text-cyan-400" size={18} />,
      accent: "border-cyan-500/30",
      badge: "3 CASAS",
    },
    {
      title: "Vácuo de Caixa (Cartões)",
      value: formatBRL(vacuoCartoes),
      sub: `${qtdCartoes.toLocaleString("pt-BR")} vendas Cartão/TEF a liquidar`,
      icon: <Wallet className="text-amber-400" size={18} />,
      accent: "border-amber-500/30",
      badge: "A RECEBER",
    },
    {
      title: "Alertas Críticos",
      value: String(criticos),
      sub:
        criticos > 0
          ? `Retenção cartão > 30 min · ${formatBRL(totais?.valorCriticoRetencao ?? 0)}`
          : "Nenhuma retenção crítica (>30 min)",
      icon: (
        <AlertTriangle
          className={cn(criticos > 0 ? "text-red-500 animate-pulse" : "text-slate-300")}
          size={18}
        />
      ),
      accent: criticos > 0 ? "border-red-500/40" : "border-white/10",
      badge: "ANTI-FRAUDE",
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
          KPIs Executivos — Tempo Real
        </span>
        {fromCache && (
          <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-[10px]">
            RAM CACHE
          </Badge>
        )}
        {loading && (
          <Badge variant="outline" className="text-[10px] text-slate-300 border-slate-600">
            atualizando…
          </Badge>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((c) => (
          <Card key={c.title} className={cn("bg-slate-900/90 border", c.accent)}>
            <CardContent className="pt-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-bold text-slate-200">{c.title}</p>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[9px] text-slate-300 border-slate-600">
                    {c.badge}
                  </Badge>
                  {c.icon}
                </div>
              </div>
              <p className="text-2xl font-bold text-white font-mono tabular-nums">{c.value}</p>
              <p className="text-xs text-slate-300">{c.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/** Autocontido: busca KPIs do cache RAM + alertas card-fraud (para dashboard legado). */
export function PresidentTopKpisLive() {
  const [totais, setTotais] = useState<TotaisDiaPista | null>(null);
  const [alertas, setAlertas] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fromCache, setFromCache] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const hoje = hojeLocalIso();
      try {
        // KPIs primeiro (paint <1s) — fraud em paralelo sem bloquear se atrasar
        const kpisPromise = fetchPresidentDashboard();
        const fraudPromise = apiService.getCardFraudAudit(hoje, hoje, undefined, null);
        const kpis = await kpisPromise;
        if (cancelled) return;
        setTotais(kpis.totaisDia);
        setFromCache(Boolean(kpis.fromCache));
        setAlertas(
          Number(kpis.fraude?.alertasCriticos ?? 0) ||
            Number(kpis.totaisDia?.alertasCriticosRetencao ?? 0) ||
            0
        );
        setLoading(false);
        const fraud = await fraudPromise.catch(() => null);
        if (cancelled) return;
        setAlertas(
          Number(fraud?.resumo?.totalCriticos ?? 0) ||
            Number(kpis.fraude?.alertasCriticos ?? 0) ||
            Number(kpis.totaisDia?.alertasCriticosRetencao ?? 0) ||
            0
        );
      } catch {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PresidentTopKpis
      totais={totais}
      alertasCriticos={alertas}
      loading={loading}
      fromCache={fromCache}
    />
  );
}
