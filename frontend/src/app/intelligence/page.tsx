"use client";
import { useEffect, useState } from "react";
import { intelligenceApi } from "@/lib/api";
import { PageHeader, StatCard, Spinner, Badge, EmptyState } from "@/components/ui";
import { TrendingUp, TrendingDown } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LineChart, Line, Legend
} from "recharts";

const SENTIMENT_COLORS = { positive: "#14b8a6", neutral: "#64748b", negative: "#ef4444" };
const PLATFORM_COLORS = ["#3b82f6", "#14b8a6", "#f59e0b", "#8b5cf6", "#ec4899", "#10b981", "#f97316"];

export default function IntelligencePage() {
  const [sentimentTrends, setSentimentTrends] = useState<any[]>([]);
  const [narratives, setNarratives] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [velocity, setVelocity] = useState<any[]>([]);
  const [normStats, setNormStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [processing, setProcessing] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      intelligenceApi.sentimentTrends(days),
      intelligenceApi.narratives(days),
      intelligenceApi.entities(days, undefined, 15),
      intelligenceApi.sourceComparison(days),
      intelligenceApi.trendVelocity(14),
      intelligenceApi.normalisationStats(),
    ]).then(([st, nar, ent, src, vel, norm]) => {
      setSentimentTrends(st.data.trends || []);
      setNarratives(nar.data.narratives || []);
      setEntities(ent.data.entities || []);
      setSources(src.data.sources || []);
      setVelocity(vel.data.velocity || []);
      setNormStats(norm.data);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [days]);

  const triggerProcess = async () => {
    setProcessing(true);
    try { await intelligenceApi.triggerProcessing(); load(); }
    catch(e) {}
    finally { setProcessing(false); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Social Intelligence</h1>
          <p className="text-sm text-slate-400 mt-1">NLP-processed discourse analysis from all sources</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2">
            {[7, 30, 90].map(d => (
              <button key={d} onClick={() => setDays(d)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${days === d ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-slate-200"}`}>
                {d}d
              </button>
            ))}
          </div>
          <button onClick={triggerProcess} disabled={processing}
            className="px-3 py-1.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium">
            {processing ? "Processing..." : "Run NLP"}
          </button>
        </div>
      </div>

      {/* Pipeline stats */}
      {normStats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard label="Raw posts" value={normStats.total_raw?.toLocaleString()} color="blue" />
          <StatCard label="Normalised" value={normStats.total_normalised?.toLocaleString()} sub={`${normStats.normalisation_rate}% rate`} color="teal" />
          <StatCard label="NLP processed" value={normStats.total_nlp_processed?.toLocaleString()} sub={`${normStats.nlp_rate}% rate`} color="purple" />
          <StatCard label="Sources tracked" value={sources.length} color="amber" />
        </div>
      )}

      {loading ? <Spinner /> : (
        <>
          {/* Sentiment trends over time */}
          <div className="card mb-6">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Sentiment trends over time</h2>
            {sentimentTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={sentimentTrends}>
                  <defs>
                    {Object.entries(SENTIMENT_COLORS).map(([k, color]) => (
                      <linearGradient key={k} id={`grad_${k}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={color} stopOpacity={0} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} unit="%" />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
                  <Area type="monotone" dataKey="positive_pct" name="Positive" stroke="#14b8a6" fill="url(#grad_positive)" strokeWidth={2} dot={false} />
                  <Area type="monotone" dataKey="neutral_pct" name="Neutral" stroke="#64748b" fill="url(#grad_neutral)" strokeWidth={1} dot={false} />
                  <Area type="monotone" dataKey="negative_pct" name="Negative" stroke="#ef4444" fill="url(#grad_negative)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyState message="No sentiment data yet. Run an ingest and then click Run NLP." />}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Narrative trends */}
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Narrative trends</h2>
              {narratives.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={narratives} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} />
                    <YAxis type="category" dataKey="narrative" tick={{ fill: "#94a3b8", fontSize: 10 }} width={120} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyState message="No narrative data yet." />}
            </div>

            {/* Source comparison */}
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Source comparison</h2>
              {sources.length > 0 ? (
                <div className="space-y-2">
                  {sources.map((s: any, i: number) => (
                    <div key={s.platform} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-28 truncate capitalize">{s.platform.replace("_", " ")}</span>
                      <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full" style={{
                          width: `${Math.min((s.total / Math.max(...sources.map((x:any) => x.total))) * 100, 100)}%`,
                          background: PLATFORM_COLORS[i % PLATFORM_COLORS.length]
                        }} />
                      </div>
                      <span className="text-xs text-slate-500 w-10 text-right">{s.total}</span>
                      <span className={`text-xs w-12 text-right ${s.avg_sentiment > 0 ? "text-teal-400" : s.avg_sentiment < 0 ? "text-red-400" : "text-slate-500"}`}>
                        {s.avg_sentiment > 0 ? "+" : ""}{(s.avg_sentiment * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : <EmptyState message="No source data yet." />}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Trend velocity */}
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Trend velocity</h2>
              {velocity.length > 0 ? (
                <div className="space-y-2">
                  {velocity.slice(0, 10).map((t: any) => (
                    <div key={t.topic} className="flex items-center gap-3">
                      <span className="text-xs text-slate-300 w-24 truncate">{t.topic}</span>
                      <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${t.trending ? "bg-teal-400" : "bg-slate-600"}`}
                          style={{ width: `${Math.min(Math.abs(t.velocity) * 100, 100)}%` }} />
                      </div>
                      <div className="flex items-center gap-1 w-16 justify-end">
                        {t.trending ? <TrendingUp size={10} className="text-teal-400" /> : <TrendingDown size={10} className="text-slate-500" />}
                        <span className={`text-xs ${t.trending ? "text-teal-400" : "text-slate-500"}`}>
                          {t.velocity > 0 ? "+" : ""}{(t.velocity * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <EmptyState message="No velocity data yet." />}
            </div>

            {/* Named entities */}
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Named entities</h2>
              {entities.length > 0 ? (
                <div className="space-y-1.5">
                  {entities.map((e: any) => (
                    <div key={`${e.entity}-${e.type}`} className="flex items-center justify-between">
                      <span className="text-xs text-slate-300 truncate max-w-[160px]">{e.entity}</span>
                      <div className="flex items-center gap-1">
                        <Badge variant={e.type === "PERSON" ? "blue" : e.type === "ORG" ? "green" : e.type === "GPE" ? "amber" : "gray"}>
                          {e.type}
                        </Badge>
                        <span className="text-xs text-slate-500 w-8 text-right">{e.count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <EmptyState message="No entities detected yet." />}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
