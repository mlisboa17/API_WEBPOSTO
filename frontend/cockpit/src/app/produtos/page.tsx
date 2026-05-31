import { CockpitShell } from "@/components/cockpit-shell";
import { ProdutosLive } from "@/components/produtos-live";

export default function ProdutosPage() {
  return (
    <CockpitShell title="Produtos">
      <ProdutosLive />
    </CockpitShell>
  );
}
