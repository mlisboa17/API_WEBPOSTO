"use client";

import React from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface InfoTooltipProps {
  content: string;
  className?: string;
}

export function InfoTooltip({ content, className }: InfoTooltipProps) {
  return (
    <span className={cn("relative inline-flex items-center group cursor-help", className)}>
      <HelpCircle size={14} className="text-slate-500 hover:text-slate-300 transition-colors" />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 w-64 p-2 text-[11px] leading-relaxed text-slate-200 bg-slate-900 border border-white/10 rounded-lg shadow-xl">
        {content}
        <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-900" />
      </span>
    </span>
  );
}
