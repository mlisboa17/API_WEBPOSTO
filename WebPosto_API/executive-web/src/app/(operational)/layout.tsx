import { Suspense } from "react";
import { SidebarV2 } from "@/components/executive/sidebar-v2";
import { MobileNav } from "@/components/executive/mobile-nav";

export default function OperationalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <Suspense fallback={<aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 border-r bg-[#0f172a] lg:block" />}>
        <SidebarV2 />
      </Suspense>
      <main className="flex-1 overflow-y-auto pb-20 lg:pb-0">
        {children}
      </main>
      <div className="lg:hidden">
        <MobileNav />
      </div>
    </div>
  );
}
