"use client";

import { Wallet } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { CashierAuditPanel } from "@/components/executive/cashier-audit-panel";
import { useGlobalFilter } from "@/contexts/global-filter-context";

export default function CashierAuditPage() {
  const { isConsolidated, selectedFilial, filialShortLabel, periodLabel } = useGlobalFilter();
  const empresaCodigo = isConsolidated ? undefined : selectedFilial;

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header>
        <div className="flex items-center gap-2 mb-1">
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
            Fast-Response
          </Badge>
          <span className="text-[10px] text-slate-300 uppercase tracking-widest font-bold">
            Cache RAM · Worker 30s
          </span>
        </div>
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
          <Wallet className="text-emerald-400" size={28} />
          Auditoria de Caixas
        </h1>
        <p className="text-slate-400 text-sm">
          Bico × Caixa × Formas de pagamento • {filialShortLabel} • {periodLabel}
        </p>
      </header>

      <GlobalFilterHeader />

      <CashierAuditPanel empresaCodigo={empresaCodigo} ready />
    </div>
  );
}
