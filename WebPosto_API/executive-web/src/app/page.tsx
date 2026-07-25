import { ExecutiveDashboard } from "@/components/executive/dashboard";
import { Sidebar } from "@/components/executive/sidebar";
import { MobileNav } from "@/components/executive/mobile-nav";
import { getTreasuryData } from "@/lib/treasury";
import { PresidencyDashboardV2 } from "@/components/executive/presidency-dashboard-v2";

interface PageProps { searchParams: Promise<{ start?: string; end?: string; company?: string; department?: string; basis?: string; view?: string }> }
export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const start = params.start || "2026-07-01";
  const end = params.end || "2026-07-18";
  const company = params.company || "all";
  const department = params.department || "all";
  const basis = params.basis === "caixa" ? "caixa" : "competencia";
  if (params.view !== "details") {
    const details = new URLSearchParams({ start, end, company, department, basis, view: "details" });
    return <div className="flex min-h-screen"><PresidencyDashboardV2 day={end} detailsHref={`/?${details}`}/></div>;
  }
  const data = await getTreasuryData(start, end, company, department);
  return <div className="flex min-h-screen pb-20 lg:pb-0"><Sidebar/><ExecutiveDashboard data={data} start={start} end={end} company={company} department={department} basis={basis}/><MobileNav/></div>;
}
