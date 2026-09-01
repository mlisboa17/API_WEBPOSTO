"use client";

import React from "react";
import { Building2 } from "lucide-react";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  COPILOT_ALL_UNITS_LABEL,
  COPILOT_PUBLIC_UNITS,
  type CopilotPublicUnitName,
  type CopilotUnitSelection,
} from "@/types/executive_copilot";
import { cn } from "@/lib/utils";

interface UnitSelectorProps {
  value: CopilotUnitSelection;
  onChange: (next: CopilotUnitSelection) => void;
  className?: string;
}

const OPTIONS = [
  { value: COPILOT_ALL_UNITS_LABEL, label: COPILOT_ALL_UNITS_LABEL },
  ...COPILOT_PUBLIC_UNITS.map((unit) => ({
    value: unit.publicName,
    label: unit.publicName,
  })),
];

export function UnitSelector({ value, onChange, className }: UnitSelectorProps) {
  const handleChange = (raw: string) => {
    if (raw === COPILOT_ALL_UNITS_LABEL) {
      onChange({ kind: "all", publicName: COPILOT_ALL_UNITS_LABEL });
      return;
    }
    const match = COPILOT_PUBLIC_UNITS.find((unit) => unit.publicName === raw);
    if (!match) return;
    onChange({
      kind: "unit",
      publicName: match.publicName as CopilotPublicUnitName,
      code: match.code,
    });
  };

  return (
    <div className={cn("flex items-center gap-2 flex-1 min-w-0", className)} data-testid="copilot-unit-selector">
      <div className="grid size-8 place-items-center rounded-md bg-blue-500/10 shrink-0">
        <Building2 size={16} className="text-blue-400" />
      </div>
      <Select
        value={value.publicName}
        onChange={handleChange}
        options={OPTIONS}
        placeholder="Selecione a unidade"
        className="flex-1 min-w-[220px]"
      />
      <Badge
        variant="outline"
        className={cn(
          "text-xs font-medium hidden sm:inline-flex",
          value.kind === "all"
            ? "bg-blue-500/10 text-blue-300 border-blue-500/20"
            : "bg-purple-500/10 text-purple-300 border-purple-500/20"
        )}
      >
        {value.publicName}
      </Badge>
    </div>
  );
}
