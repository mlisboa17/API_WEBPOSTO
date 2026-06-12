"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { StatementsImport } from "@/components/statements/statements-import";
import { StatementsOverview } from "@/components/statements/statements-overview";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { StatementTab } from "@/types/statements";
import { FileUpIcon, LandmarkIcon } from "lucide-react";

const TABS: { value: StatementTab; label: string; icon: React.ComponentType<{ className?: string }> }[] =
  [
    { value: "overview", label: "Extratos", icon: LandmarkIcon },
    { value: "import", label: "Importação", icon: FileUpIcon },
  ];

function normalizeTab(raw: string | null): StatementTab {
  return raw === "import" ? "import" : "overview";
}

export function StatementsTabs() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeTab = normalizeTab(searchParams.get("tab"));

  const onTabChange = useCallback(
    (value: StatementTab) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === "overview") {
        params.delete("tab");
      } else {
        params.set("tab", value);
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return (
    <Tabs value={activeTab} onValueChange={(v) => onTabChange(normalizeTab(v))} className="flex flex-1 flex-col">
      <div className="border-b bg-card/40 px-4 pt-4 lg:px-6">
        <TabsList variant="line" className="w-full justify-start">
          {TABS.map(({ value, label, icon: Icon }) => (
            <TabsTrigger key={value} value={value} className="gap-1.5">
              <Icon className="size-4" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>

      <TabsContent value="overview" className="mt-0 flex-1">
        <StatementsOverview />
      </TabsContent>
      <TabsContent value="import" className="mt-0 flex-1">
        <StatementsImport />
      </TabsContent>
    </Tabs>
  );
}

export function StatementsTabsFallback() {
  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="h-8 w-64 animate-pulse rounded-md bg-muted" />
      <div className="h-40 animate-pulse rounded-lg bg-muted" />
      <div className="h-64 animate-pulse rounded-lg bg-muted" />
    </div>
  );
}
