"use client";
import { useState } from "react";
import { motion } from "motion/react";
import { BarChart3, Building2, ChevronLeft, Droplets, Landmark, Package, ReceiptText, Settings2, WalletCards } from "lucide-react";
import { cn } from "@/lib/utils";
const NAV = [{ label: "Dashboard", icon: BarChart3 }, { label: "Financeiro", icon: WalletCards }, { label: "Tesouraria", icon: Landmark, active: true }, { label: "Fiscal", icon: ReceiptText }, { label: "Combustíveis", icon: Droplets }, { label: "Produtos", icon: Package }, { label: "Administração", icon: Settings2 }];
export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  return <motion.aside animate={{ width: collapsed ? 76 : 248 }} className="sticky top-0 hidden h-screen shrink-0 border-r bg-[#0f172a] text-slate-300 lg:flex lg:flex-col">
    <div className="flex h-20 items-center gap-3 border-b border-white/10 px-5"><span className="grid size-9 place-items-center rounded-lg bg-blue-500 text-white"><Building2 size={18}/></span>{!collapsed && <div><strong className="block text-sm text-white">LOGOS</strong><span className="text-xs text-slate-500">Executive Finance</span></div>}</div>
    <nav aria-label="Navegação principal" className="flex-1 space-y-1 p-3">{NAV.map(({ label, icon: Icon, active }) => <button key={label} className={cn("flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm transition hover:bg-white/5 hover:text-white", active && "bg-blue-500/15 text-blue-300")} aria-current={active ? "page" : undefined}><Icon size={18}/>{!collapsed && <span>{label}</span>}</button>)}</nav>
    <button onClick={() => setCollapsed(v => !v)} className="m-3 flex h-10 items-center justify-center rounded-lg border border-white/10 hover:bg-white/5" aria-label={collapsed ? "Expandir menu" : "Recolher menu"}><ChevronLeft className={cn("transition", collapsed && "rotate-180")} size={18}/></button>
  </motion.aside>;
}
