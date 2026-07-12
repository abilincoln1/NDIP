"use client";
import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner, EmptyState } from "@/components/ui";
import { engagementApi } from "@/lib/api";
import { Activity } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";

const TYPE_COLORS: Record<string, string> = {
  registration: "#3b82f6",
  event_attendance: "#14b8a6",
  newsletter: "#f59e0b",
  content_interaction: "#8b5cf6",
  survey_response: "#ec4899",
  volunteer: "#10b981",
};

export default function EngagementPage() {
  const [summary, setSummary] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    engagementApi.summary(days)
      .then((r) => setSummary(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const byTypeData = summary?.by_type
    ? Object.entries(summary.by_type).map(([name, value]) => ({ name, value: Number(value) }))
    : [];

  return (
    <div>
      <PageHeader title="Engagement Tracking" subtitle="Aggregated interaction metrics — no individual profiling" />

      {/* Time range selector */}
      <div className="flex gap-2 mb-6">
        {[7, 30, 90, 365].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              days === d
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {d === 365 ? "1 year" : `${d}d`}
          </button>
        ))}
      </div>

      {loading ? (
        <Spinner />
      ) : !summary ? (
        <EmptyState message="Could not load engagement data." />
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total engagements" value={summary.total_engagements.toLocaleString()} icon={<Activity size={18} />} color="blue" />
            <StatCard label="Engagement index" value={summary.engagement_index.toFixed(3)} sub="Interactions per participant" color="teal" />
            <StatCard label="Growth rate" value={`${(summary.growth_rate * 100).toFixed(1)}%`} trend={summary.growth_rate} color="purple" />
            <StatCard label="Period" value={`${summary.period_days}d`} sub="Analysis window" color="amber" />
          </div>

          {/* Breakdown chart */}
          <div className="card mb-6">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Engagement by type</h2>
            {byTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={byTypeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {byTypeData.map((entry) => (
                      <Cell key={entry.name} fill={TYPE_COLORS[entry.name] || "#6366f1"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="No engagement events recorded yet. Use POST /engagement to ingest events." />
            )}
          </div>

          {/* Funnel representation */}
          <div className="card">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Engagement funnel</h2>
            <div className="space-y-2">
              {["registration", "newsletter", "event_attendance", "survey_response", "volunteer"].map((type, i) => {
                const count = summary.by_type[type] || 0;
                const max = Math.max(...Object.values(summary.by_type as Record<string, number>), 1);
                const pct = (count / max) * 100;
                return (
                  <div key={type} className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-36 shrink-0 capitalize">{type.replace("_", " ")}</span>
                    <div className="flex-1 bg-slate-800 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all duration-700"
                        style={{ width: `${pct}%`, background: TYPE_COLORS[type] || "#6366f1" }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 w-10 text-right tabular-nums">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
