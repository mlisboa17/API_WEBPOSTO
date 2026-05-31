import { CockpitShell } from "@/components/cockpit-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function VendasPage() {
  return (
    <CockpitShell title="Vendas">
      <div className="p-4 lg:p-6">
        <Card className="omie-card">
          <CardHeader>
            <CardTitle className="text-white">Vendas por período</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground">
            Em breve: tabela TanStack + proxy <code className="text-cyan-300">/api/v1/proxy/VENDA</code>.
          </CardContent>
        </Card>
      </div>
    </CockpitShell>
  );
}
