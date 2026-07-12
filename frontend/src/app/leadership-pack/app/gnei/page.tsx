"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Globe, TrendingUp, TrendingDown, Minus, Target, Clock, AlertTriangle } from "lucide-react";

const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";
const CONF = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-white";
const SENT = (s: string) => s === "positive" ? "text-teal-400" : s === "negative" ? "text-red-400" : "text-white";
const MOM = (d: string) => d === "rising" ? <TrendingUp size={13} className="text-teal-400"/> : d === "falling" ? <TrendingDown size={13} className="text-red-400"/> : <Minus size={13} className="text-white"/>;

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs text-white">{label}</span>
        <span className={`text-xs font-bold ${color}`}>{value}</span>
      </div>
      <div className="bg-slate-800 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color.replace('text-', 'bg-')}`} style={{ width: value + "%" }} />
      </div>
    </div>
  );
}

export default function GNEIPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/gnei/?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Globe size={20} className="text-blue-400" />
            <h1 className="text-3xl font-bold text-white">Global Nigerian Engagement Index</h1>
          </div>
          <p className="text-white text-sm">GNEI · How Nigeria and Nigerians are discussed and engaged with globally</p>
          <p className="text-xs text-white mt-1 italic">NDIP flagship intelligence capability · Powered by RTIFN</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
            {[{d:3,l:"3d"},{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"}].map(({d,l}) => (
              <button key={d} onClick={() => setDays(d)}
                className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors " + (days===d?"bg-blue-600 text-white":"text-white hover:text-white")}>
                {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner /><p className="text-white text-sm">Computing Global Nigerian Engagement Index...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white">Unable to load GNEI.</p></div>
      ) : (
        <div className="space-y-6">

          {/* GNEI Score Hero */}
          <div className="bg-gradient-to-br from-blue-900/40 to-slate-900 border border-blue-700/40 rounded-2xl p-7">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-1">Global Nigerian Engagement Index</p>
                <div className="flex items-baseline gap-3">
                  <span className="text-6xl font-bold text-white">{data.gnei_score}</span>
                  <span className="text-2xl text-white">/100</span>
                  <span className="text-xl font-semibold text-blue-400">{data.gnei_label}</span>
                </div>
                <p className="text-xs text-white mt-2">{new Date(data.generated_at).toLocaleString()} · {data.period_days}d window · <span className={CONF(data.confidence)}>{data.confidence} confidence</span></p>
              </div>
              <div className="text-right">
                <p className="text-xs text-white mb-1">Sources</p>
                <p className="text-2xl font-bold text-white">{data.source_count}</p>
                <p className="text-xs text-white mt-2">GNEI Records</p>
                <p className="text-2xl font-bold text-white">{data.total_gnei_records?.toLocaleString()}</p>
              </div>
            </div>

            {/* Component Scores */}
            <div className="grid grid-cols-5 gap-3 mb-5">
              {[
                { label: "Diaspora", value: data.component_scores?.diaspora_engagement, color: "text-blue-400" },
                { label: "Sentiment", value: data.component_scores?.global_sentiment, color: "text-teal-400" },
                { label: "International", value: data.component_scores?.international_attention, color: "text-purple-400" },
                { label: "Opportunity", value: data.component_scores?.opportunity, color: "text-amber-400" },
                { label: "Diversity", value: data.component_scores?.narrative_diversity, color: "text-white" },
              ].map((item, i) => (
                <div key={i} className="bg-slate-800/50 rounded-xl p-3 text-center">
                  <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
                  <p className="text-xs text-white mt-1">{item.label}</p>
                </div>
              ))}
            </div>

            <p className="text-white text-base leading-relaxed">{data.assessment?.what_happened}</p>
          </div>

          {/* Why It Matters + What Changed */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Target size={16} className="text-amber-400" />
                <h2 className="text-sm font-bold text-white">Why It Matters</h2>
              </div>
              <p className="text-sm text-white leading-relaxed">{data.assessment?.why_it_matters}</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp size={16} className="text-teal-400" />
                <h2 className="text-sm font-bold text-white">What Changed</h2>
              </div>
              <p className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{ __html: b(data.assessment?.what_changed || "") }} />
            </div>
          </div>

          {/* Strategic Implications */}
          {(data.assessment?.strategic_implications || []).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-bold text-white mb-3">Strategic Implications</h2>
              <div className="space-y-2">
                {data.assessment.strategic_implications.map((imp: string, i: number) => (
                  <div key={i} className="flex items-start gap-2 p-3 bg-slate-800/40 rounded-lg">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 mt-1.5" />
                    <p className="text-sm text-white leading-relaxed">{imp}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* GNEI Narrative Breakdown */}
          {(data.gnei_narratives || []).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-bold text-white mb-4">Global Nigerian Narrative Breakdown</h2>
              <div className="space-y-3">
                {data.gnei_narratives.map((n: any) => (
                  <div key={n.narrative} className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-white">{n.narrative}</span>
                        {MOM(n.momentum_direction)}
                        <span className="text-xs text-white">{n.momentum > 0 ? "+" : ""}{n.momentum?.toFixed(0)}%</span>
                      </div>
                      <div className="bg-slate-700 rounded-full h-1">
                        <div className="bg-blue-500 h-1 rounded-full" style={{ width: Math.min(n.share_of_voice * 2, 100) + "%" }} />
                      </div>
                    </div>
                    <span className={`text-xs ${SENT(n.sentiment_label)}`}>{n.sentiment_label}</span>
                    <span className="text-sm font-bold text-white tabular-nums w-12 text-right">{n.share_of_voice}%</span>
                    <span className="text-xs text-white w-20 text-right">{n.count?.toLocaleString()} mentions</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outlook */}
          <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Clock size={15} className="text-white" />
              <h2 className="text-sm font-bold text-white">GNEI Outlook</h2>
            </div>
            <p className="text-sm text-white leading-relaxed">{data.outlook}</p>
          </div>

        </div>
      )}
    </div>
  );
}
