"use client";

import { useState } from "react";
import { Eraser, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { clearBrowserCache, hardReload } from "@/lib/clear-browser-cache";

type Props = {
  collapsed?: boolean;
  className?: string;
  /** Variante compacta (só ícone + label curto). */
  variant?: "sidebar" | "inline";
};

export function ClearBrowserCacheButton({
  collapsed = false,
  className,
  variant = "sidebar",
}: Props) {
  const [busy, setBusy] = useState(false);

  const onClick = async () => {
    if (busy) return;
    const ok = window.confirm(
      "Limpar cache do navegador neste site?\n\n" +
        "Será apagado: localStorage, sessionStorage, Cache API e Service Workers.\n" +
        "Filtros salvos (filial/período) serão resetados.\n" +
        "A página será recarregada em seguida."
    );
    if (!ok) return;

    setBusy(true);
    try {
      await clearBrowserCache();
    } finally {
      hardReload();
    }
  };

  if (variant === "inline") {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={busy}
        title="Limpar cache do navegador e recarregar"
        className={cn(
          "inline-flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-medium text-amber-200 transition hover:bg-amber-500/20 disabled:opacity-60",
          className
        )}
      >
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Eraser size={14} />}
        Limpar cache do navegador
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      title="Limpar cache do navegador (storage + Cache API) e recarregar"
      aria-label="Limpar cache do navegador"
      className={cn(
        "flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm text-amber-200/90 transition hover:bg-amber-500/10 hover:text-amber-100 disabled:opacity-60",
        className
      )}
    >
      {busy ? <Loader2 size={18} className="animate-spin shrink-0" /> : <Eraser size={18} className="shrink-0" />}
      {!collapsed && <span className="truncate">Limpar cache</span>}
    </button>
  );
}
