import type { Metadata } from "next";
import "./globals.css";
import "./globals-override.css";
import Sidebar from "@/components/layout/Sidebar";
import AICopilot, { CopilotProvider } from "@/components/ui/AICopilot";

export const metadata: Metadata = {
  title: "NDIP | National & Diaspora Intelligence Platform",
  description: "National & Diaspora Intelligence Platform — Understanding Nigeria. Understanding the Diaspora. Informing Leadership.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden">
        <CopilotProvider>
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-slate-950 p-6 lg:p-8">
            {children}
          </main>
          <AICopilot />
        </CopilotProvider>
      </body>
    </html>
  );
}
