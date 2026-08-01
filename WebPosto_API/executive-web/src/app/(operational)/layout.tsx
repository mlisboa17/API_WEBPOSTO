import { SidebarV2 } from "@/components/executive/sidebar-v2";
import { MobileNav } from "@/components/executive/mobile-nav";

export default function OperationalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <SidebarV2 />
      <main className="flex-1 overflow-y-auto pb-20 lg:pb-0">
        {children}
      </main>
      <div className="lg:hidden">
        <MobileNav />
      </div>
    </div>
  );
}
