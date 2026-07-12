"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { TrendingUp, TrendingDown, Minus, BarChart2, Activity } from "lucide-react";
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";

const TREND_ICON = (t: string) => {
  if (t.includes("growth") || t.includes("acceleration")) return <TrendingUp size={14} className="text-teal-400" />;
  if (t.includes("decline") || t.includes("deceleration")) return <TrendingDown size={14} className="text-red-400" />;
  return <Minus size={14} className="text-slate-400" />;
};
const TREND_COLOR = (t: string) =>
  t.includes("growth") || t.includes("acceleration") ? "text-teal-400" :
  t.includes("decline") || t.includes("deceleration") ? "text-red-400" : "text-slate-400";

export default function HistoricalPage() {
  const [overview, setOverview] = useState<any>(null);
  const [sentiment, setSentiment] = useState<any>(null);
  const [narratives, setNarratives] = useState<any>(null);
  const [participation, setParticipation] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/historical/overview"),
      api.get("/historical/sentiment?days=" + days),
      api.get("/historical/narratives?days=" + days),
      api.get("/historical/participation"),
    ]).then(([ov, sent, nar, part]) => {
      setOverview(ov.data);
      setSentiment(sent.data);
      setNarratives(nar.data);
      setParticipation(part.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [days]);

  const boldify = (text: string) =>
    text?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Historical Intelligence</h1>
          <p className="text-slate-400 text-sm">Trend analysis · Narrative shifts · Participation history</p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={"px-3 py-2 rounded-lg text-xs font-medium transition-colors " + (days === d ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white")}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? <div className="flex justify-center py-24"><Spinner /></div> : (
        <div className="space-y-6">

          {/* Period comparison */}
          {overview && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {overview.periods.map((p: any) => (
                <div key={p.days} className="card">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{p.period}</span>
                    <div className="flex items-center gap-1">
                      {TREND_ICON(p.sentiment_trend)}
                      <span className={"text-xs " + TREND_COLOR(p.sentiment_trend)}>{p.sentiment_trend}</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-500">Posts analysed</span>
                      <span className="text-xs font-medium text-white">{p.total_posts.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-500">Engagement index</span>
                      <span className="text-xs font-medium text-white">{p.engagement_index.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-500">Dominant narrative</span>
                      <span className="text-xs font-medium text-blue-300 truncate max-w-[100px]">{p.dominant_narrative}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-500">Fastest rising</span>
                      <span className="text-xs font-medium text-teal-300 truncate max-w-[100px]">{p.fastest_rising}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-slate-500">Narratives tracked</span>
                      <span className="text-xs font-medium text-white">{p.narrative_count}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Sentiment trend chart */}
          {sentiment && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity size={18} className="text-blue-400" />
                  <h2 className="text-base font-bold text-white">Sentiment Trend ({days} days)</h2>
                </div>
                <div className="flex items-center gap-2">
                  {TREND_ICON(sentiment.trend_type)}
                  <span className={"text-sm font-medium " + TREND_COLOR(sentiment.trend_type)}>
                    {sentiment.trend_type}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500 mb-4">{sentiment.summary}</p>
              {sentiment.data?.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={sentiment.data}>
                    <defs>
                      <linearGradient id="sentGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                    <YAxis tick={{ fill: "#64748b", fontSize: 10 }} domain={[-1, 1]} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="avg_score" name="Sentiment" stroke="#3b82f6" fill="url(#sentGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-500 text-sm text-center py-8">No sentiment data available for this period.</p>
              )}
              {sentiment.shifts?.length > 0 && (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Significant Shifts Detected</p>
                  {sentiment.shifts.map((s: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      {s.direction.includes("positive") ?
                        <TrendingUp size={12} className="text-teal-400" /> :
                        <TrendingDown size={12} className="text-red-400" />}
                      <span className="text-slate-400">{s.date}:</span>
                      <span className={s.direction.includes("positive") ? "text-teal-300" : "text-red-300"}>
                        {s.direction} (magnitude: {(s.magnitude * 100).toFixed(0)}%)
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Narrative shifts */}
          {narratives && (
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 size={18} className="text-purple-400" />
                <h2 className="text-base font-bold text-white">Narrative Shifts ({days} days)</h2>
              </div>
              {!narratives.narrative_shifts?.length ? (
                <p className="text-slate-500 text-sm">No significant narrative shifts detected in this period.</p>
              ) : (
                <div className="space-y-3">
                  {narratives.narrative_shifts.map((s: any, i: number) => (
                    <div key={i} className={"p-3 rounded-xl border " + (s.direction === "increasing" ? "border-teal-700/30 bg-teal-900/10" : "border-red-700/30 bg-red-900/10")}>
                      <div className="flex items-center gap-2 mb-1">
                        {s.direction === "increasing" ?
                          <TrendingUp size={14} className="text-teal-400" /> :
                          <TrendingDown size={14} className="text-red-400" />}
                        <span className="text-sm font-semibold text-white">{s.narrative}</span>
                        <span className={"ml-auto text-xs font-bold " + (s.direction === "increasing" ? "text-teal-400" : "text-red-400")}>
                          {s.change > 0 ? "+" : ""}{s.change}%
                        </span>
                      </div>
                      <p className="text-xs text-slate-400"
                        dangerouslySetInnerHTML={{ __html: boldify(s.plain_english) }} />
                      <div className="flex gap-4 mt-2 text-xs text-slate-600">
                        <span>Current: {s.current_sov}%</span>
                        <span>Previous: {s.previous_sov}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Participation history */}
          {participation && participation.data?.length > 0 && (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity size={18} className="text-teal-400" />
                  <h2 className="text-base font-bold text-white">Engagement History</h2>
                </div>
                <div className="flex items-center gap-2">
                  {TREND_ICON(participation.trend_type)}
                  <span className={"text-sm font-medium " + TREND_COLOR(participation.trend_type)}>
                    {participation.trend_type}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500 mb-4">{participation.summary}</p>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={participation.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
                  <Line type="monotone" dataKey="engagement_index" name="Engagement Index" stroke="#14b8a6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
