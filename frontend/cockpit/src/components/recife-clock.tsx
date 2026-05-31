"use client";

import { useEffect, useState } from "react";

import { nowRecifeLabel } from "@/lib/datetime-br";

/** Relógio em America/Recife — renderizado só no client para evitar hydration mismatch. */
export function RecifeClock() {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    const tick = () => setLabel(nowRecifeLabel());
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);

  return <span>{label ?? "…"}</span>;
}
