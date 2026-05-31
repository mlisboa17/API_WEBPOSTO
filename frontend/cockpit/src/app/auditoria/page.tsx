import { CockpitShell } from "@/components/cockpit-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AuditoriaPage() {
  return (
    <CockpitShell title="Auditoria">
      <div className="p-4 lg:p-6">
        <Card className="omie-card">
          <CardHeader>
            <CardTitle className="text-white">Fechamento & subcentros</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground">
            Em breve: fluxo de <code className="text-cyan-300">theme/audit_subcentro.js</code> com jobs
            202 em <code className="text-cyan-300">/api/v1/audit/process</code>.
          </CardContent>
        </Card>
      </div>
    </CockpitShell>
  );
}
