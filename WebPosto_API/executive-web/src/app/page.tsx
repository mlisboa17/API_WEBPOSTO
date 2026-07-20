import { ExecutiveDashboard } from "@/components/executive/dashboard";
import { Sidebar } from "@/components/executive/sidebar";
import { MobileNav } from "@/components/executive/mobile-nav";
import { getTreasuryData } from "@/lib/treasury";

interface PageProps { searchParams: Promise<{ start?: string; end?: string; company?: string; department?: string; basis?: string }> }
export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const start = params.start || "2026-07-01";
  const end = params.end || "2026-07-18";
  const company = params.company || "all";
  const department = params.department || "all";
  const basis = params.basis === "caixa" ? "caixa" : "competencia";
  const data = await getTreasuryData(start, end, company, department);
  return <div className="flex min-h-screen pb-20 lg:pb-0"><Sidebar/><ExecutiveDashboard data={data} start={start} end={end} company={company} department={department} basis={basis}/><MobileNav/></div>;
}
