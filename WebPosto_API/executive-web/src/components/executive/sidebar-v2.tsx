"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import {
  Building2,
  ChevronLeft,
  Droplets,
  LayoutDashboard,
  AlertCircle,
  Settings2,
  TrendingUp,
  Truck,
  Landmark,
  Wallet,
  Fuel,
  ClipboardCheck,
  Scale,
  Timer,
  Gauge,
  Users,
  Trophy,
  Target,
  LineChart,
  Layers,
  Activity,
  Tags,
  PackagePlus,
  FileInput,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ClearBrowserCacheButton } from "@/components/executive/clear-browser-cache-button";

type NavItem = {
  id: string;
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  inactive?: boolean;
  badge?: string;
};

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "Operacional",
    items: [
      { id: "op-cockpit", label: "Cockpit de Pista Ao Vivo", href: "/executive/live-feed", icon: Fuel },
      { id: "op-cockpit-30s", label: "Cockpit 30s", href: "/operational/cockpit-30s", icon: Timer },
      { id: "op-tanks", label: "Tanques & Telemetria", href: "/operational/tanks", icon: Droplets },
      {
        id: "op-price-update",
        label: "Atualização de Preços",
        href: "/produtos/atualizacao-precos",
        icon: Tags,
      },
      {
        id: "op-product-register",
        label: "Cadastrar Produto",
        href: "/produtos/cadastrar",
        icon: PackagePlus,
      },
      {
        id: "op-fiscal-models",
        label: "Modelos Fiscais",
        href: "/produtos/modelos-fiscais",
        icon: Scale,
      },
      {
        id: "op-nfe-entrada",
        label: "NF-e de Entrada",
        href: "/fiscal/nfe-entrada",
        icon: FileInput,
      },
      { id: "op-sales", label: "Vendas & Elasticidade", href: "/dashboard/sales-analytics", icon: TrendingUp },
      { id: "op-logistics", label: "Logística de Frete", href: "/dashboard/logistics", icon: Truck },
      {
        id: "op-bombas",
        label: "Bombas & Vazão",
        href: "#bombas-vazao",
        icon: Gauge,
        inactive: true,
        badge: "Em Breve",
      },
    ],
  },
  {
    title: "Financeiro",
    items: [
      { id: "fin-dre", label: "DRE Executiva", href: "/executive/financial?tab=dre", icon: LineChart },
      {
        id: "fin-multi",
        label: "DRE Multi-Dimensional",
        href: "/executive/financial?tab=multidim",
        icon: Layers,
      },
      {
        id: "fin-prestacao",
        label: "Prestação & Conciliação",
        href: "/financial/reconciliation",
        icon: Scale,
      },
      {
        id: "fin-expense-review",
        label: "Revisão de Despesas",
        href: "/executive/financial/expense-review",
        icon: ClipboardCheck,
      },
      { id: "fin-cashier", label: "Auditoria de Caixas", href: "/executive/cashier-audit", icon: Wallet },
      { id: "fin-treasury", label: "Tesouraria & Sweep", href: "/dashboard/treasury", icon: Landmark },
    ],
  },
  {
    title: "Pessoas / RH",
    items: [
      {
        id: "rh-frentista",
        label: "Produtividade do Frentista",
        href: "/executive/live-feed",
        icon: Users,
      },
      {
        id: "rh-rankings",
        label: "Rankings de Equipe",
        href: "/executive/financial?tab=multidim",
        icon: Trophy,
      },
      {
        id: "rh-vales",
        label: "Conta Corrente Vales & Faltas",
        href: "/financial/reconciliation",
        icon: Activity,
      },
      {
        id: "rh-metas",
        label: "Metas de Aditivados",
        href: "#metas-aditivados",
        icon: Target,
        inactive: true,
        badge: "Em Breve",
      },
    ],
  },
  {
    title: "Diretoria",
    items: [
      {
        id: "dir-copilot",
        label: "Copiloto Executivo",
        href: "/executive/copilot",
        icon: Bot,
      },
      {
        id: "dir-dashboard",
        label: "Dashboard Executivo & Score",
        href: "/executive/financial",
        icon: LayoutDashboard,
      },
      {
        id: "dir-benchmark",
        label: "Benchmark de Filiais",
        href: "/executive/financial?tab=benchmark",
        icon: Building2,
      },
      {
        id: "dir-units",
        label: "Unidades Consolidadas",
        href: "/executive/units-consolidated",
        icon: Building2,
      },
      {
        id: "dir-postos",
        label: "Inteligência dos Postos",
        href: "/executive/postos-inteligencia",
        icon: Fuel,
      },
      {
        id: "dir-audit",
        label: "Aferição de Dados",
        href: "/executive/data-audit",
        icon: ClipboardCheck,
      },
      { id: "dir-alerts", label: "Gestão de Alertas", href: "/executive/alerts", icon: AlertCircle },
      {
        id: "dir-settings",
        label: "Configurações do Sistema",
        href: "/executive/settings",
        icon: Settings2,
      },
    ],
  },
];

function parseHref(href: string): { path: string; tab: string | null } {
  const [path, query = ""] = href.split("?");
  const tab = new URLSearchParams(query).get("tab");
  return { path, tab };
}

/** Destaca item com suporte a deep-link `?tab=` no hub financeiro. */
function isNavActive(pathname: string, searchTab: string | null, href: string): boolean {
  const { path, tab: hrefTab } = parseHref(href);
  if (pathname !== path && !pathname.startsWith(`${path}/`)) return false;

  if (path === "/executive/financial") {
    const current = searchTab || "overview";
    if (!hrefTab) return current === "overview";
    return current === hrefTab;
  }

  return pathname === path || pathname.startsWith(`${path}/`);
}

export function SidebarV2() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname() || "";
  const searchParams = useSearchParams();
  const searchTab = searchParams.get("tab");

  return (
    <motion.aside
      animate={{ width: collapsed ? 76 : 248 }}
      className="sticky top-0 hidden h-screen shrink-0 border-r bg-[#0f172a] text-slate-300 lg:flex lg:flex-col"
    >
      <div className="flex h-20 items-center gap-3 border-b border-white/10 px-5">
        <span className="grid size-9 place-items-center rounded-lg bg-blue-500 text-white">
          <Building2 size={18} />
        </span>
        {!collapsed && (
          <div>
            <strong className="block text-sm text-white">LOGOS</strong>
            <span className="text-xs text-slate-500">UX 3.0 · Intelligence</span>
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
            {group.items.map(({ id, label, href, icon: Icon, inactive, badge }) => {
              if (inactive) {
                return (
                  <div
                    key={id}
                    title="Recurso em desenvolvimento"
                    aria-disabled="true"
                    className={cn(
                      "flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm",
                      "opacity-50 text-slate-500 bg-slate-900/50 border border-slate-800 cursor-not-allowed pointer-events-none select-none"
                    )}
                  >
                    <Icon size={18} className="shrink-0 text-slate-500" />
                    {!collapsed && (
                      <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
                        <span className="truncate">{label}</span>
                        <span className="bg-slate-800 text-slate-400 text-[10px] px-2 py-0.5 rounded border border-slate-700 font-semibold uppercase shrink-0">
                          {badge || "Em Breve"}
                        </span>
                      </span>
                    )}
                  </div>
                );
              }

              const active = isNavActive(pathname, searchTab, href);
              return (
                <Link
                  key={id}
                  href={href}
                  className={cn(
                    "flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm transition hover:bg-white/5 hover:text-white",
                    active && "bg-blue-500/15 text-blue-300 border-l-2 border-blue-500"
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && <span className="truncate">{label}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-white/10 space-y-1">
        <ClearBrowserCacheButton collapsed={collapsed} />
      </div>

      <button
        onClick={() => setCollapsed((v) => !v)}
        className="m-3 flex h-10 items-center justify-center rounded-lg border border-white/10 hover:bg-white/5"
        aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
      >
        <ChevronLeft className={cn("transition", collapsed && "rotate-180")} size={18} />
      </button>
    </motion.aside>
  );
}
