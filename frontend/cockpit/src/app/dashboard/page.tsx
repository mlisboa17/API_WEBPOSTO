import { CockpitShell } from "@/components/cockpit-shell";
import { DashboardLive } from "@/components/dashboard-live";

export default function DashboardPage() {
  return (
    <CockpitShell title="Painel Gerencial">
      <DashboardLive />
    </CockpitShell>
  );
}
