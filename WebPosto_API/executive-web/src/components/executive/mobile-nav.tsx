"use client";

import { BarChart3, Landmark, Menu, ReceiptText, WalletCards } from "lucide-react";

const items = [
  { label: "Dashboard", icon: BarChart3 },
  { label: "Financeiro", icon: WalletCards },
  { label: "Tesouraria", icon: Landmark, active: true },
  { label: "Fiscal", icon: ReceiptText },
];

export function MobileNav() {
  return (
    <nav aria-label="Navegação móvel" className="fixed inset-x-3 bottom-3 z-50 flex h-16 items-center justify-around rounded-2xl border border-white/10 bg-[#0f172a]/95 px-2 text-slate-400 shadow-2xl backdrop-blur lg:hidden">
      {items.map(({ label, icon: Icon, active }) => (
        <button key={label} aria-current={active ? "page" : undefined} className={active ? "grid min-w-14 place-items-center gap-1 text-blue-300" : "grid min-w-14 place-items-center gap-1 hover:text-white"}>
          <Icon size={18} />
          <span className="text-[10px]">{label}</span>
        </button>
      ))}
      <button aria-label="Abrir demais módulos" className="grid min-w-12 place-items-center gap-1 hover:text-white">
        <Menu size={18} />
        <span className="text-[10px]">Mais</span>
      </button>
    </nav>
  );
}
