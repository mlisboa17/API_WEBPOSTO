"use client";

import { ReportFilterProvider } from "@/contexts/report-filter-context";

export default function ReportsLayout({ children }: { children: React.ReactNode }) {
  return <ReportFilterProvider>{children}</ReportFilterProvider>;
}
