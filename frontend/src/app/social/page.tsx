"use client";
import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner, Badge, EmptyState } from "@/components/ui";
import { socialApi } from "@/lib/api";
import { Radio, TrendingUp, AlertCircle } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend
} from "recharts";

const SENTIMENT_COLORS = { positive: "#14b8a6", neutral: "#64748b", negative: "#ef4444" };

export default function SocialPage() {
  const [overview, setOverview] = useState<any>(null);
  const [sentiment, setSentiment] = useState<any>(null);
  const [topics, setTopics] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingestQuery, setIngestQuery] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<any>(null);

  useEffect(() => {
    Promise.all([socialApi.overview(), socialApi.sentiment(30), socialApi.topics(7, 20)])
      .then(([o, s, t]) => {
        setOverview(o.data);
        setSentiment(s.data);
        setTopics(t.data.topics || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const runIngest = async () => {
    if (!ingestQuery.trim()) return;
    setIngesting(true);
    try {
      const r = await socialApi.ingest(ingestQuery);
      setIngestResult(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setIngesting(false);
    }
  };

  if (loading) return <Spinner />;

  const sentimentPie = sentiment
    ? [
        { name: "Positive", value: sentiment.positive_pct },
        { name: "Neutral",  value: sentiment.neutral_pct },
        { name: "Negative", value: sentiment.negative_pct },
      ]
    : [];

  const platformData = overview?.platform_counts
    ? Object.entries(overview.platform_counts).map(([k, v]) => ({ platform: k, count: v }))
    : [];

  return (
    <div>
      <PageHeader
        title="Social Intelligence"
        subtitle="Public discourse analysis via official APIs — aggregated, anonymised"
      />

      {/* Connector status */}
      <div className="card mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Radio size={14} className="text-blue-400" />
          <h2 className="text-sm font-semibold text-slate-300">Connector status</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {overview?.connector_status?.map((c: any) => (
            <div key={c.platform} className="flex items-center gap-1.5 bg-slate-800 rounded-lg px-3 py-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${c.configured ? "bg-teal-400" : "bg-slate-600"}`} />
              <span className="text-xs text-slate-300 capitalize">{c.platform}</span>
              <span className="text-xs text-slate-600">{c.configured ? "active" : "not configured"}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total posts analysed" value={(overview?.total_posts_analysed || 0).toLocaleString()} color="blue" />
        <StatCard label="Sentiment score" value={(sentiment?.overall_score || 0).toFixed(2)} sub="-1 to +1" color="teal" />
        <StatCard label="Positive %" value={`${(sentiment?.positive_pct || 0).toFixed(1)}%`} color="teal" />
        <StatCard label="Topics tracked (7d)" value={topics.length} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Sentiment pie */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Sentiment distribution</h2>
          {sentimentPie.some(s => s.value > 0) ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={sentimentPie} dataKey="value" cx="50%" cy="50%" outerRadius={70} stroke="none">
                  {sentimentPie.map((entry) => (
                    <Cell key={entry.name} fill={(SENTIMENT_COLORS as any)[entry.name.toLowerCase()]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any) => `${Number(v).toFixed(1)}%`} contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <EmptyState message="No sentiment data. Run an ingest first." />}
        </div>

        {/* Topics bar chart */}
        <div className="card lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Top topics (7 days)</h2>
          {topics.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={topics.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} width={90} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyState message="No topics detected yet." />}
        </div>
      </div>

      {/* Platform breakdown */}
      {platformData.length > 0 && (
        <div className="card mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Posts by platform</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={platformData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="platform" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Ingest trigger */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp size={14} className="text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-300">Trigger data ingest</h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Fetch public posts from configured connectors. Only official APIs are used. No individual data is stored.
        </p>
        <div className="flex gap-3">
          <input
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            placeholder="Search query (e.g. diaspora community Africa UK)"
            value={ingestQuery}
            onChange={(e) => setIngestQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runIngest()}
          />
          <button
            onClick={runIngest}
            disabled={ingesting}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap"
          >
            {ingesting ? "Running..." : "Run ingest"}
          </button>
        </div>
        {ingestResult && (
          <div className="mt-4 bg-slate-800 rounded-lg p-3">
            <p className="text-xs text-slate-400 font-mono whitespace-pre-wrap">
              {JSON.stringify(ingestResult.summary, null, 2)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
