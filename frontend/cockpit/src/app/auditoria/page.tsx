import { CockpitShell } from "@/components/cockpit-shell";
import { AuditoriaDashboard } from "@/components/auditoria-dashboard";

export default function AuditoriaPage() {
  return (
    <CockpitShell title="Auditoria">
      <AuditoriaDashboard />
    </CockpitShell>
  );
}
