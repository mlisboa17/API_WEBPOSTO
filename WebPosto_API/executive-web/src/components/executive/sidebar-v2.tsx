"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import { 
  Building2, 
  ChevronLeft, 
  Droplets, 
  LayoutDashboard, 
  AlertCircle, 
  Calculator, 
  Settings2,
  TrendingUp,
  Truck,
  Landmark,
  Wallet,
  FileText
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_GROUPS = [
  {
    title: "Visão Estratégica",
    items: [
      { label: "Cockpit 30s", href: "/dashboard/executive", icon: LayoutDashboard },
      { label: "Gestão de Alertas", href: "/executive/alerts", icon: AlertCircle },
      { label: "Simulador de Margem", href: "/executive/simulator", icon: Calculator },
    ]
  },
  {
    title: "Analytics",
    items: [
      { label: "Vendas & Elasticidade", href: "/dashboard/sales-analytics", icon: TrendingUp },
      { label: "Logística de Frete", href: "/dashboard/logistics", icon: Truck },
      { label: "Tesouraria & Sweep", href: "/dashboard/treasury", icon: Landmark },
      { label: "Central de Relatórios", href: "/executive/reports", icon: FileText },
    ]
  },
  {
    title: "Operações",
    items: [
      { label: "Centro Financeiro", href: "/executive/financial-center", icon: Wallet },
      { label: "Tanques e Pista", href: "/operational/tanks", icon: Droplets },
    ]
  }
];

export function SidebarV2() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <motion.aside 
      animate={{ width: collapsed ? 76 : 248 }} 
      className="sticky top-0 hidden h-screen shrink-0 border-r bg-[#0f172a] text-slate-300 lg:flex lg:flex-col"
    >
      <div className="flex h-20 items-center gap-3 border-b border-white/10 px-5">
        <span className="grid size-9 place-items-center rounded-lg bg-blue-500 text-white">
          <Building2 size={18}/>
        </span>
        {!collapsed && (
          <div>
            <strong className="block text-sm text-white">LOGOS</strong>
            <span className="text-xs text-slate-500">Executive Intelligence</span>
          </div>
        )}
      </div>

      <nav aria-label="Navegação principal" className="flex-1 space-y-6 p-3 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="space-y-1">
            {!collapsed && (
              <p className="px-3 text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">
                {group.title}
              </p>
            )}
            {group.items.map(({ label, href, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(href + '/');
              return (
                <Link 
                  key={href} 
                  href={href}
                  className={cn(
                    "flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm transition hover:bg-white/5 hover:text-white", 
                    active && "bg-blue-500/15 text-blue-300 border-l-2 border-blue-500"
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon size={18}/>
                  {!collapsed && <span className="truncate">{label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-white/10">
         <Link 
            href="#"
            className="flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm transition hover:bg-white/5 hover:text-white"
          >
            <Settings2 size={18}/>
            {!collapsed && <span>Configurações</span>}
          </Link>
      </div>

      <button 
        onClick={() => setCollapsed(v => !v)} 
        className="m-3 flex h-10 items-center justify-center rounded-lg border border-white/10 hover:bg-white/5" 
        aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
      >
        <ChevronLeft className={cn("transition", collapsed && "rotate-180")} size={18}/>
      </button>
    </motion.aside>
  );
}
