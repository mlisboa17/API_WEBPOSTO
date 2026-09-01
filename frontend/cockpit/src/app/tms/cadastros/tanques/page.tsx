import { CockpitShell } from "@/components/cockpit-shell";
import { TmsTanquesAdmin } from "@/components/tms-tanques-admin";

export default function TmsTanquesPage() {
  return (
    <CockpitShell title="TMS - Cadastro de Tanques">
      <TmsTanquesAdmin />
    </CockpitShell>
  );
}
