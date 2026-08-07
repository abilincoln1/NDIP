"use client";
/**
 * NDIP Phase D.3 — Member Dashboard (D3.11)
 * File: frontend/src/app/dashboard/page.tsx
 *
 * Displays:
 *   - Profile completion percentage
 *   - Impact score (current + rank)
 *   - Engagement reports summary
 *   - Sponsorships summary
 *   - Projects summary
 *   - Verification status
 *   - Recent notifications
 *   - Quick actions
 *
 * Admin panel (chapter_admin, national_director, super_admin):
 *   - Member count
 *   - Pending verifications
 *   - Active projects
 *   - Failed notifications
 *   - Platform stats
 */

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_ROLES = ["chapter_admin", "national_director", "super_admin"];

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
}

async function apiFetch<T>(path: string): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  return (json.data ?? json) as T;
}

interface MemberSummary {
  id: string;
  email: string;
  full_name: string;
  membership_number: string;
  role: string;
  membership_tier: string;
  is_verified: boolean;
  is_active: boolean;
  chapter_id: string | null;
}

interface OnboardingState {
  completion_pct: number;
  wizard_completed: boolean;
  email_verified: boolean;
  photo_uploaded: boolean;
  profile_completed: boolean;
}

interface ImpactScore {
  total_score: number;
  chapter_rank: number | null;
  national_rank: number | null;
  reports_score: number;
  sponsorship_score: number;
  projects_score: number;
  verification_bonus: number;
}

interface PlatformStats {
  total_members: number;
  active_members: number;
  verified_members: number;
  total_chapters: number;
  approved_reports: number;
  pending_verifications: number;
  active_projects: number;
  failed_notifications: number;
}

interface Notification {
  id: string;
  event_type: string;
  subject: string;
  status: string;
  created_at: string;
}

// ─── Stat card ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: {
  label: string; value: string | number; sub?: string; accent?: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${accent ?? "text-gray-800"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

// ─── Badge ─────────────────────────────────────────────────────────────────

function Badge({ text, color }: { text: string; color: "green" | "yellow" | "red" | "blue" | "gray" }) {
  const map = {
    green: "bg-green-100 text-green-800",
    yellow: "bg-yellow-100 text-yellow-800",
    red: "bg-red-100 text-red-800",
    blue: "bg-blue-100 text-blue-800",
    gray: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${map[color]}`}>
      {text}
    </span>
  );
}

// ─── Quick action ──────────────────────────────────────────────────────────

function QuickAction({ href, label, icon }: { href: string; label: string; icon: string }) {
  return (
    <Link
      href={href}
      className="flex flex-col items-center p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:border-blue-300 hover:shadow-md transition-all gap-2"
    >
      <span className="text-2xl">{icon}</span>
      <span className="text-xs font-medium text-gray-700 text-center">{label}</span>
    </Link>
  );
}

// ─── Main dashboard ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [member, setMember] = useState<MemberSummary | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [impact, setImpact] = useState<ImpactScore | null>(null);
  const [platformStats, setPlatformStats] = useState<PlatformStats | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) { router.push("/login"); return; }

    Promise.allSettled([
      apiFetch<MemberSummary>("/api/v2/auth/me"),
      apiFetch<OnboardingState>("/api/v2/auth/onboarding"),
      apiFetch<ImpactScore>("/api/v2/impact/me"),
    ]).then(([memberRes, onboardingRes, impactRes]) => {
      if (memberRes.status === "fulfilled") {
        setMember(memberRes.value);
        // Load admin stats if applicable
        if (ADMIN_ROLES.includes(memberRes.value.role)) {
          apiFetch<PlatformStats>("/api/v2/admin/platform-stats")
            .then(setPlatformStats).catch(() => {});
        }
      } else {
        router.push("/login"); return;
      }
      if (onboardingRes.status === "fulfilled") setOnboarding(onboardingRes.value);
      if (impactRes.status === "fulfilled") setImpact(impactRes.value);

      // Load recent notifications (best-effort)
      apiFetch<Notification[]>("/api/v2/members/notifications?limit=5")
        .then(setNotifications).catch(() => {});

      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!member) return null;

  const isAdmin = ADMIN_ROLES.includes(member.role);
  const pct = onboarding?.completion_pct ?? 0;

  return (
    <div className="min-h-screen bg-gray-50 py-6 px-4">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {member.full_name.split(" ")[0]}
            </h1>
            <p className="text-gray-500 text-sm mt-0.5">
              {member.membership_number} · {member.role.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex gap-2 flex-wrap justify-end">
            <Badge
              text={member.is_verified ? "Verified" : "Unverified"}
              color={member.is_verified ? "green" : "yellow"}
            />
            <Badge text={member.membership_tier} color="blue" />
          </div>
        </div>

        {/* Onboarding incomplete banner */}
        {onboarding && !onboarding.wizard_completed && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-medium text-blue-800 text-sm">
                Your profile is {pct}% complete
              </p>
              <p className="text-blue-600 text-xs mt-0.5">
                Complete your onboarding to unlock all platform features
              </p>
            </div>
            <Link
              href="/onboarding"
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 whitespace-nowrap"
            >
              Continue Setup →
            </Link>
          </div>
        )}

        {/* Impact + Profile stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Impact Score"
            value={impact ? Math.round(impact.total_score) : "—"}
            sub={impact?.national_rank ? `National rank #${impact.national_rank}` : "Not yet ranked"}
            accent="text-blue-700"
          />
          <StatCard
            label="Chapter Rank"
            value={impact?.chapter_rank ? `#${impact.chapter_rank}` : "—"}
            sub="Within your chapter"
          />
          <StatCard
            label="Profile"
            value={`${pct}%`}
            sub={pct === 100 ? "Complete" : "Completion"}
            accent={pct === 100 ? "text-green-600" : "text-orange-500"}
          />
          <StatCard
            label="Status"
            value={member.is_verified ? "Verified" : "Unverified"}
            sub={member.is_verified ? "Identity confirmed" : "Verification pending"}
            accent={member.is_verified ? "text-green-600" : "text-yellow-600"}
          />
        </div>

        {/* Admin panel */}
        {isAdmin && platformStats && (
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Platform Overview</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Members"    value={platformStats.total_members}         />
              <StatCard label="Active Members"   value={platformStats.active_members}         />
              <StatCard label="Verified Members" value={platformStats.verified_members}       />
              <StatCard label="Chapters"         value={platformStats.total_chapters}         />
              <StatCard label="Approved Reports" value={platformStats.approved_reports}       />
              <StatCard
                label="Pending Verifications"
                value={platformStats.pending_verifications}
                accent={platformStats.pending_verifications > 0 ? "text-orange-600" : undefined}
              />
              <StatCard label="Active Projects"  value={platformStats.active_projects}        />
              <StatCard
                label="Failed Notifications"
                value={platformStats.failed_notifications}
                accent={platformStats.failed_notifications > 0 ? "text-red-600" : undefined}
              />
            </div>
          </div>
        )}

        {/* Impact breakdown */}
        {impact && impact.total_score > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-base font-semibold text-gray-800 mb-4">Impact Score Breakdown</h2>
            {[
              { label: "Engagement Reports", value: impact.reports_score, max: 100 },
              { label: "Ward Sponsorships",  value: impact.sponsorship_score, max: 100 },
              { label: "Project Participation", value: impact.projects_score, max: 50 },
              { label: "Verification Bonus", value: impact.verification_bonus, max: 25 },
            ].map(item => (
              <div key={item.label} className="mb-3">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{item.label}</span>
                  <span className="font-medium text-gray-800">{item.value} / {item.max}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${Math.min((item.value / item.max) * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Recent notifications */}
        {notifications.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Recent Notifications</h2>
            <div className="space-y-2">
              {notifications.map(n => (
                <div key={n.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800">{n.subject || n.event_type}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {new Date(n.created_at).toLocaleDateString()} ·{" "}
                      <Badge
                        text={n.status}
                        color={n.status === "sent" ? "green" : n.status === "failed" ? "red" : "gray"}
                      />
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-3">Quick Actions</h2>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            <QuickAction href="/api/v2/reports/my"       label="My Reports"      icon="📋" />
            <QuickAction href="/api/v2/sponsorships"      label="Sponsorships"    icon="🏗️" />
            <QuickAction href="/api/v2/projects"          label="Projects"        icon="🚀" />
            <QuickAction href="/api/v2/verification/my"   label="Verification"    icon="✅" />
            <QuickAction href="/onboarding"               label="Profile Setup"   icon="👤" />
            {isAdmin && (
              <QuickAction href="/api/v2/admin/members"   label="Manage Members"  icon="⚙️" />
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-gray-400 pb-4">
          NDIP · Phase D.3 Platform Readiness · RTIFN
        </div>
      </div>
    </div>
  );
}
