"use client";
import { useEffect, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";
import { Users, Activity, TrendingUp, Heart, AlertTriangle } from "lucide-react";
import { StatCard, PageHeader, Spinner, EmptyState } from "@/components/ui";
import { analyticsApi, engagementApi } from "@/lib/api";

const COLORS = ["#3b82f6", "#14b8a6", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [engagementData, setEngagementData] = useState<any>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      analyticsApi.overview(30),
      analyticsApi.engagement(30),
      analyticsApi.trend("engagement_index", 90),
    ])
      .then(([m, e, t]) => {
        setMetrics(m.data);
        setEngagementData(e.data);
        setTrend(t.data.trend || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (!metrics) return <EmptyState message="Unable to load analytics. Check API connection." />;

  const byType = engagementData?.by_type
    ? Object.entries(engagementData.by_type).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div>
      <PageHeader
        title="Observatory Overview"
        subtitle="Aggregated engagement metrics · last 30 days"
      />

      {/* Stat grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total participants"
          value={metrics.total_participants.toLocaleString()}
          icon={<Users size={18} />}
          trend={metrics.growth_rate}
          sub="Opt-in registrants"
          color="blue"
        />
        <StatCard
          label="Engagement index"
          value={metrics.engagement_index.toFixed(2)}
          icon={<Activity size={18} />}
          sub="Interactions per participant"
          color="teal"
        />
        <StatCard
          label="Participation rate"
          value={`${(metrics.participation_index * 100).toFixed(1)}%`}
          icon={<TrendingUp size={18} />}
          sub="Active in period"
          color="purple"
        />
        <StatCard
          label="Sentiment score"
          value={metrics.sentiment_score.toFixed(2)}
          icon={<Heart size={18} />}
          sub="-1.0 negative → +1.0 positive"
          color="amber"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Engagement trend */}
        <div className="lg:col-span-2 card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Engagement index trend</h2>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="blue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(d) => d.slice(5, 10)} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} labelStyle={{ color: "#94a3b8" }} />
                <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="url(#blue)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState message="No historical snapshots yet. Generate one via /analytics/snapshot." />
          )}
        </div>

        {/* Engagement by type */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Engagement by type</h2>
          {byType.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={byType} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={75} stroke="none">
                  {byType.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState message="No engagement events recorded yet." />
          )}
        </div>
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="New participants (7d)" value={metrics.new_participants_7d} color="blue" />
        <StatCard label="Total engagements" value={metrics.total_engagements.toLocaleString()} color="teal" />
        <StatCard label="Growth rate" value={`${(metrics.growth_rate * 100).toFixed(1)}%`} color="purple" />
        <StatCard label="Topic momentum" value={metrics.topic_momentum_score.toFixed(2)} color="amber" sub="0 = stable" />
      </div>
    </div>
  );
}
