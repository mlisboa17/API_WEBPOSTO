import { Suspense } from "react";

import { CockpitShell } from "@/components/cockpit-shell";
import {
  StatementsTabs,
  StatementsTabsFallback,
} from "@/components/statements/statements-tabs";

export default function StatementsPage() {
  return (
    <CockpitShell title="Extratos e Importação">
      <Suspense fallback={<StatementsTabsFallback />}>
        <StatementsTabs />
      </Suspense>
    </CockpitShell>
  );
}
