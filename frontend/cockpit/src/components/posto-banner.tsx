"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AdelaideMetrics } from "@/types/metrics";
import { Building2Icon } from "lucide-react";

export function PostoBanner({
  data,
  loading,
}: {
  data?: AdelaideMetrics | null;
  loading?: boolean;
}) {
  const u = data?.unidade;

  return (
    <Card className="omie-hero mx-4 lg:mx-6">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="omie-kpi-icon size-12 rounded-xl">
              <Building2Icon className="size-6" />
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Unidade · WebPosto
              </p>
              <CardTitle className="text-2xl font-bold">
                {loading ? <Skeleton className="h-8 w-48" /> : u?.fantasia ?? "POSTO VIP"}
              </CardTitle>
              <div className="mt-1 text-sm text-muted-foreground">
                {loading ? (
                  <Skeleton className="h-4 w-72" />
                ) : (
                  <>
                    {u?.razao_social ?? "RIO DOCE COMERCIO E SERVICOS LTDA"}
                    {u?.cnpj ? ` · CNPJ ${u.cnpj}` : ""}
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Grupo Lisboa</Badge>
            {data?.status_api && (
              <Badge variant={data.dados_reais ? "default" : "outline"}>
                {data.dados_reais ? "Dados reais" : data.status_api}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      {data?.mensagem && !data.dados_reais && (
        <CardContent className="text-sm text-amber-600 dark:text-amber-400">
          {data.mensagem}
        </CardContent>
      )}
    </Card>
  );
}
