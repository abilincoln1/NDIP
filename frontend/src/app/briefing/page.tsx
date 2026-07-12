"use client";
import { useEffect, useState } from "react";
import { briefingApi } from "@/lib/api";
import { PageHeader, StatCard, Spinner, Badge, EmptyState } from "@/components/ui";
import { TrendingUp, TrendingDown, AlertTriangle, Info, CheckCircle, Newspaper } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function BriefingPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    briefingApi.executive(days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <Spinner />;
  if (!data) return <EmptyState message="Unable to load briefing. Run an ingest first." />;

  const sentimentColor = data.sentiment_shift > 0 ? "text-teal-400" : data.sentiment_shift < 0 ? "text-red-400" : "text-slate-400";
  const SentimentIcon = data.sentiment_shift > 0 ? TrendingUp : TrendingDown;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Executive Briefing</h1>
          <p className="text-sm text-slate-400 mt-1">Intelligence summary · {new Date(data.generated_at).toLocaleString()}</p>
        </div>
        <div className="flex gap-2">
          {[3, 7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${days === d ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-slate-200"}`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Executive Summary */}
      <div className="card mb-6 border-l-4 border-l-blue-500">
        <div className="flex items-start gap-3">
          <Newspaper size={18} className="text-blue-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Executive Summary</p>
            <p className="text-slate-200 text-sm leading-relaxed">{data.executive_summary}</p>
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Posts Analysed" value={data.posts_analysed.toLocaleString()} color="blue" />
        <StatCard label="Engagement Index" value={data.metrics.engagement_index.toFixed(2)} color="teal" />
        <StatCard label="Sentiment Shift" value={`${data.sentiment_shift > 0 ? "+" : ""}${(data.sentiment_shift * 100).toFixed(1)}%`} color={data.sentiment_shift >= 0 ? "teal" : "red"} />
        <StatCard label="Emerging Topics" value={data.emerging_topics.length} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Anomalies */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Anomalies & Alerts</h2>
          {data.anomalies.length === 0 ? (
            <div className="flex items-center gap-2 text-teal-400">
              <CheckCircle size={16} /> <span className="text-sm">No anomalies detected</span>
            </div>
          ) : (
            <div className="space-y-2">
              {data.anomalies.map((a: any, i: number) => (
                <div key={i} className={`flex items-start gap-2 p-3 rounded-lg ${a.type === "alert" ? "bg-red-500/10" : a.type === "warning" ? "bg-amber-500/10" : "bg-blue-500/10"}`}>
                  <AlertTriangle size={14} className={a.type === "alert" ? "text-red-400" : a.type === "warning" ? "text-amber-400" : "text-blue-400"} />
                  <p className="text-xs text-slate-300">{a.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Key Insights */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Key Intelligence Findings</h2>
          {data.key_insights.length === 0 ? (
            <EmptyState message="No insights yet — run an ingest to populate." />
          ) : (
            <div className="space-y-2">
              {data.key_insights.map((insight: string, i: number) => (
                <div key={i} className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                  <p className="text-sm text-slate-300">{insight}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Narratives */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Top Narratives</h2>
          {data.top_narratives.length === 0 ? <EmptyState message="No narratives yet." /> : (
            <div className="space-y-2">
              {data.top_narratives.map((n: any) => (
                <div key={n.narrative_id} className="flex items-center justify-between">
                  <span className="text-xs text-slate-300 truncate">{n.narrative}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs ${n.avg_sentiment > 0 ? "text-teal-400" : n.avg_sentiment < 0 ? "text-red-400" : "text-slate-500"}`}>
                      {n.avg_sentiment > 0 ? "+" : ""}{(n.avg_sentiment * 100).toFixed(0)}%
                    </span>
                    <Badge variant="gray">{n.count}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Entities */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Top Entities</h2>
          {data.top_entities.length === 0 ? <EmptyState message="No entities yet." /> : (
            <div className="space-y-2">
              {data.top_entities.slice(0, 8).map((e: any) => (
                <div key={e.entity} className="flex items-center justify-between">
                  <span className="text-xs text-slate-300 truncate">{e.entity}</span>
                  <div className="flex items-center gap-1">
                    <Badge variant="blue">{e.type}</Badge>
                    <Badge variant="gray">{e.count}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Emerging Topics */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Emerging Topics</h2>
          {data.emerging_topics.length === 0 ? <EmptyState message="No emerging topics yet." /> : (
            <div className="space-y-2">
              {data.emerging_topics.map((t: any) => (
                <div key={t.topic} className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">{t.topic}</span>
                  <div className="flex items-center gap-1">
                    <TrendingUp size={12} className="text-teal-400" />
                    <span className="text-xs text-teal-400">+{(t.velocity * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
