"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";

const NAV = [
  { name: "MSI Completion Dashboard", href: "/manager-dashboard" },
  { name: "Technician Efficiency", href: "/manager-dashboard/technician-efficiency" },
  { name: "Service Quality Metrics", href: "/manager-dashboard/service-quality-metrics" },
  { name: "RO Explorer", href: "/manager-dashboard/ro-explorer" },
  { name: "Upload Daily Report", href: "/manager-dashboard/daily-report" },
];

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  function handleLogout() {
    // Clear only the session cookies; do NOT clear auth_banned (if present)
    document.cookie = "auth_session=; Path=/; Max-Age=0; SameSite=Lax";
    document.cookie = "auth_exp=; Path=/; Max-Age=0; SameSite=Lax";
    // Redirect to home (signin)
    window.location.href = "/";
  }

  return (
    <main className="min-h-screen bg-white text-zinc-900 dark:bg-[#0b0b0b] dark:text-white">
      <div className="grid min-h-screen md:grid-cols-[260px_1fr]">
        {/* Sidebar */}
        <aside
          className={`fixed top-0 z-30 h-screen w-64 flex-col justify-between border-r border-zinc-200 bg-zinc-50 p-4 transition-transform dark:border-white/10 dark:bg-[#121212] md:sticky md:flex md:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div>
            <div className="mb-20 flex items-center gap-3 px-2">
              <div className="grid h-9 w-9 place-items-center">
                <Image
                  src="/toyota-logo.png"
                  alt="Toyota G.T Motors logo"
                  width={120}
                  height={120}
                  className="mx-auto mb-3"
                  priority
                />
              </div>
              <div>
                <p className="text-sm font-semibold leading-tight text-zinc-800 dark:text-white">TOYOTA G.T MOTORS</p>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Manager Admin Panel</p>
              </div>
            </div>

            <nav className="space-y-1">
              {NAV.map((item) => {
                const active =
                  pathname === item.href ||
                  (item.href === "/manager-dashboard" && pathname === "/manager-dashboard");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition text-zinc-700 dark:text-zinc-300
                      ${
                        active
                          ? "bg-red-100 text-red-700 ring-1 ring-red-200 dark:bg-red-600/15 dark:text-white dark:ring-red-600/40"
                          : "hover:bg-zinc-200/50 dark:hover:bg-white/5"
                      }`}
                    aria-current={active ? "page" : undefined}
                  >
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Footer actions */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleLogout}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-100 px-3 py-2 text-left text-sm text-zinc-700 transition hover:bg-zinc-200 focus:outline-none focus:ring-2 focus:ring-red-500/60 dark:border-white/10 dark:bg-white/5 dark:text-zinc-300 dark:hover:bg-white/10"
              aria-label="Logout"
              title="Logout"
            >
              Logout
            </button>

            <p className="px-3 text-xs text-zinc-500">
              &copy; {new Date().getFullYear()} Toyota G.T Motors. All rights reserved.
            </p>
          </div>
        </aside>

        {/* Main Content */}
        <section className="min-h-screen">
          <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-white/10 dark:bg-[#0b0b0b]/80 md:hidden">
            <div className="flex items-center justify-between px-4 py-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-lg border border-zinc-200 bg-zinc-100 p-2 text-zinc-800 hover:bg-zinc-200 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
                aria-label="Open sidebar"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="3" y1="12" x2="21" y2="12"></line>
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
              </button>
              <p className="text-sm font-semibold text-zinc-800 dark:text-white">TOYOTA G.T MOTORS</p>
            </div>
          </header>

          {/* Overlay for mobile */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 z-20 bg-black/60 md:hidden"
              onClick={() => setSidebarOpen(false)}
              aria-hidden="true"
            />
          )}

          <div className="mx-auto max-w-7xl px-4 py-6">{children}</div>
        </section>
      </div>
    </main>
  );
}
