"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, Activity, Globe, FileText,
  Radio, LogOut, Brain, Shield, AlertCircle,
  BookOpen, Clock, Star, Zap, Vote, Database, List, GitBranch, Cpu, Award, Target
} from "lucide-react";
import clsx from "clsx";
// NDIP brand mark — pulse/signal line above the NDIP letters, inside a
// rounded teal square. Equal top/bottom margins, pulse and lettering
// pulled together as one centered block (see brand exploration).
function NdipLogo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 180 180" aria-hidden="true">
      <rect x="0" y="0" width="180" height="180" rx="28" fill="#0C7A63" />
      <path
        d="M 22 69 L 48 69 L 60 47 L 76 87 L 92 51 L 106 69 L 158 69"
        fill="none" stroke="#FFFFFF" strokeWidth="7"
        strokeLinecap="round" strokeLinejoin="round"
      />
      <circle cx="92" cy="51" r="7" fill="#F2B33D" />
      <text
        x="90" y="133" textAnchor="middle"
        fontFamily="Arial, sans-serif" fontSize="44" fontWeight="500"
        letterSpacing="1" fill="#FFFFFF"
      >
        NDIP
      </text>
    </svg>
  );
}
const NAV_GROUPS = [
  {
    label: "EXECUTIVE",
    items: [
      { href: "/leadership-pack",   label: "Leadership Pack",      icon: Star },
      { href: "/watchlist",          label: "Leadership Watchlist", icon: List },
      { href: "/situation-room",    label: "Situation Room",       icon: AlertCircle },
      { href: "/brief",             label: "Sentinel Brief",       icon: BookOpen },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { href: "/national-pulse",    label: "National Pulse",       icon: Zap },
      { href: "/gnei",               label: "GNEI",                 icon: Globe },
      { href: "/polarisation",      label: "Polarisation",         icon: GitBranch },
      { href: "/decision-quality",  label: "Decision Quality",     icon: Brain },
      { href: "/intelligence-performance", label: "Intelligence Performance", icon: Award },
      { href: "/strategic-outcome",  label: "Strategic Outcome Intel.",  icon: Target },
      { href: "/strategic-outcome/admin", label: "Registry Management", icon: Database },
      { href: "/election-centre",   label: "Election Centre",      icon: Vote },
      { href: "/historical",        label: "Historical Trends",    icon: Clock },
      { href: "/intelligence",      label: "Entity Intelligence",  icon: Brain },
      { href: "/social",            label: "Source Monitor",       icon: Radio },
    ],
  },
  {
    label: "ANALYTICS",
    items: [
      { href: "/",                  label: "Overview",             icon: LayoutDashboard },
      { href: "/participants",      label: "Participants",         icon: Users },
      { href: "/engagement",        label: "Engagement",           icon: Activity },
    ],
  },
  {
    label: "REPORTING",
    items: [
      { href: "/reports",           label: "Reports",              icon: FileText },
      { href: "/data-health",       label: "Data Health",          icon: Shield },
    ],
  },
];
export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-64 shrink-0 flex flex-col bg-slate-900 border-r border-slate-800 h-full">
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5 mb-1">
          <NdipLogo size={32} />
          <p className="text-sm font-bold text-white leading-tight">NDIP</p>
        </div>
        <p className="text-xs text-slate-400 leading-snug">National & Diaspora Intelligence Platform</p>
        <p className="text-xs text-slate-600 mt-1 italic">Understanding Nigeria. Understanding the Diaspora.</p>
      </div>
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        {NAV_GROUPS.map(group => (
          <div key={group.label} className="mb-5">
            <p className="text-xs font-semibold text-slate-600 uppercase tracking-widest px-3 mb-1">{group.label}</p>
            <div className="space-y-0.5">
              {group.items.map(({ href, label, icon: Icon }) => {
                const active = path === href || (href !== "/" && path.startsWith(href));
                return (
                  <Link key={href} href={href}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                      active ? "bg-blue-600/20 text-blue-300 font-medium" : "text-slate-300 hover:text-white hover:bg-slate-800"
                    )}>
                    <Icon size={15} />{label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="px-3 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-600 text-center mb-2">v6.1 · RTIFN</p>
        <button
          onClick={() => { localStorage.removeItem("agora_token"); window.location.href = "/login"; }}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors">
          <LogOut size={15} />Sign out
        </button>
      </div>
    </aside>
  );
}
