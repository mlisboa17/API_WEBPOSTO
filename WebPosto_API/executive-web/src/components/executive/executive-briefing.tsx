"use client";

import { useCallback, useEffect, useState } from "react";
import { Fuel, TrendingUp, Truck, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { apiService } from "@/lib/api";
import { cn } from "@/lib/utils";

type Highlight = { tipo: string; titulo: string; texto: string };

const ICONS: Record<string, typeof Fuel> = {
  volumetria: Fuel,
  margem: TrendingUp,
  logistica: Truck,
};

export function ExecutiveBriefing({
  empresaCodigo,
  dataReferencia,
  filialLabel,
  className,
}: {
  empresaCodigo?: number;
  /** Data de referência do briefing (alinhada ao período do GlobalFilter) */
  dataReferencia?: string;
  /** Rótulo da filial do topo — exibido no card para auditoria visual */
  filialLabel?: string;
  className?: string;
}) {
  const [items, setItems] = useState<Highlight[]>([]);
  const [refDate, setRefDate] = useState("");
  const [scopedCode, setScopedCode] = useState<number | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getExecutiveBriefing(dataReferencia, empresaCodigo);
      setItems(data.destaques || []);
      setRefDate(data.dataReferencia || dataReferencia || "");
      setScopedCode(
        typeof (data as { empresaCodigo?: number | null }).empresaCodigo === "number"
          ? (data as { empresaCodigo: number }).empresaCodigo
          : empresaCodigo ?? null
      );
    } catch {
      setItems([]);
      setScopedCode(empresaCodigo ?? null);
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo, dataReferencia]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <Skeleton className={cn("h-28 w-full", className)} />;
  }
  if (!items.length) return null;

  const scopeBadge =
    filialLabel ||
    (scopedCode != null ? `Filial ${scopedCode}` : "Consolidado");

  return (
    <Card
      className={cn(
        "border-slate-800 bg-slate-900/90 overflow-hidden",
        className
      )}
    >
      <CardContent className="p-4 lg:p-5">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <Sparkles size={16} className="text-amber-400" />
          <p className="text-sm font-bold text-white">Briefing Executivo</p>
          <Badge
            variant="outline"
            className="text-[10px] border-purple-500/30 text-purple-200 bg-purple-500/10"
          >
            {scopeBadge}
          </Badge>
          <Badge
            variant="outline"
            className="text-[10px] border-slate-700 text-slate-300"
          >
            Ref. {refDate}
          </Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {items.map((item) => {
            const Icon = ICONS[item.tipo] || Sparkles;
            return (
              <div
                key={item.tipo}
                className="rounded-lg border border-slate-800 bg-slate-950/60 p-3"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <Icon size={14} className="text-sky-300 shrink-0" />
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                    {item.titulo}
                  </p>
                </div>
                <p className="text-sm text-slate-200 leading-snug">{item.texto}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
