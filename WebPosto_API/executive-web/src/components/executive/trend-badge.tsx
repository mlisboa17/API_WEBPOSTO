"use client";

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export function TrendBadge({
  value,
  label = "vs. período anterior",
  invert = false,
  className,
}: {
  value: number | null | undefined;
  label?: string;
  /** Se true, alta é ruim (ex: despesas). */
  invert?: boolean;
  className?: string;
}) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-300",
          className
        )}
      >
        <Minus size={10} />
        s/ base
      </span>
    );
  }

  const up = value > 0.05;
  const down = value < -0.05;
  const good = invert ? down : up;
  const bad = invert ? up : down;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-semibold",
        good && "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
        bad && "border-rose-500/30 bg-rose-500/10 text-rose-300",
        !good && !bad && "border-white/10 bg-white/5 text-slate-400",
        className
      )}
      title={label}
    >
      {up ? <ArrowUpRight size={11} /> : down ? <ArrowDownRight size={11} /> : <Minus size={11} />}
      {value > 0 ? "+" : ""}
      {value.toFixed(1)}% {label}
    </span>
  );
}

export function DailyAvgBadge({
  value,
  format,
}: {
  value: number;
  format: (n: number) => string;
}) {
  return (
    <span className="inline-flex items-center rounded-md border border-cyan-500/25 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-medium text-cyan-300">
      Média diária {format(value)}
    </span>
  );
}
