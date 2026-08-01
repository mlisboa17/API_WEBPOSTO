"use client";

import { SidebarV2 } from "@/components/executive/sidebar-v2";
import { MobileNav } from "@/components/executive/mobile-nav";
import { GlobalFilterProvider } from "@/contexts/global-filter-context";

export default function ExecutiveLayout({ children }: { children: React.ReactNode }) {
  return (
    <GlobalFilterProvider>
      <div className="flex min-h-screen bg-background">
        <SidebarV2 />
        <main className="flex-1 overflow-y-auto pb-20 lg:pb-0">{children}</main>
        <div className="lg:hidden">
          <MobileNav />
        </div>
      </div>
    </GlobalFilterProvider>
  );
}
