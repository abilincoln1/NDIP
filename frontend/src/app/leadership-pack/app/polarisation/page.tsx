"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { GitBranch, AlertTriangle, CheckCircle, Eye, Clock } from "lucide-react";

const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";
const POL_COLOR = (s: number) => s >= 60 ? "text-red-400" : s >= 35 ? "text-amber-400" : "text-teal-400";
const POL_BG = (s: number) => s >= 60 ? "border-red-700/30 bg-red-900/10" : s >= 35 ? "border-amber-700/30 bg-amber-900/10" : "border-teal-700/20 bg-teal-900/5";
const STAB_COLOR = (s: string) => s === "Stable" ? "text-teal-400" : s === "Moderate" ? "text-amber-400" : "text-red-400";
const CONF_COLOR = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-white/40";

function SentimentBar({ pos, neg, neu }: { pos: number; neg: number; neu: number }) {
  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden w-full">
        <div className="bg-teal-500" style={{ width: pos + "%" }}/>
        <div className="bg-slate-600" style={{ width: neu + "%" }}/>
        <div className="bg-red-500" style={{ width: neg + "%" }}/>
      </div>
      <div className="flex justify-between mt-1 text-xs text-white/40">
        <span>+{pos}% positive</span>
        <span>{neu}% neutral</span>
        <span>{neg}% negative</span>
      </div>
    </div>
  );
}

export default function PolarisationPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/national-pulse/polarisation?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <GitBranch size={20} className="text-purple-400"/>
            <h1 className="text-3xl font-bold text-white">Polarisation Intelligence</h1>
          </div>
          <p className="text-white/70 text-sm">Narrative-specific convergence vs divergence · Consensus and disagreement analysis · NDIP v5.5</p>
          <p className="text-xs text-white/40 mt-1">Each narrative independently analysed using narrative-specific keyword filtering</p>
        </div>
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {[{d:3,l:"3d"},{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"}].map(({d,l}) => (
            <button key={d} onClick={() => setDays(d)}
              className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors " + (days===d?"bg-purple-600 text-white":"text-white/60 hover:text-white")}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white/60 text-sm">Computing narrative-specific polarisation...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white/60">Unable to load.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Platform Score */}
          <div className="bg-gradient-to-br from-purple-900/30 to-slate-900 border border-purple-700/30 rounded-2xl p-7">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-2">Platform Polarisation Assessment</p>
                <p className="text-white text-base leading-relaxed mb-3">{data.platform_summary}</p>
                {data.methodology_note && (
                  <p className="text-xs text-white/40 italic">{data.methodology_note}</p>
                )}
              </div>
              <div className="flex gap-6 shrink-0 ml-8">
                <div className="text-center">
                  <p className={`text-4xl font-bold ${POL_COLOR(data.platform_polarisation_score)}`}>{data.platform_polarisation_score}</p>
                  <p className="text-xs text-white/50 mt-1">Polarisation</p>
                  <p className={`text-xs font-semibold mt-0.5 ${POL_COLOR(data.platform_polarisation_score)}`}>{data.polarisation_label}</p>
                </div>
                <div className="text-center">
                  <p className="text-4xl font-bold text-teal-400">{data.platform_consensus_score}</p>
                  <p className="text-xs text-white/50 mt-1">Consensus</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs text-white/40 pt-3 border-t border-purple-700/20">
              <div className="flex items-center gap-1"><div className="w-3 h-2 rounded bg-teal-500"/><span>Positive</span></div>
              <div className="flex items-center gap-1"><div className="w-3 h-2 rounded bg-slate-600"/><span>Neutral</span></div>
              <div className="flex items-center gap-1"><div className="w-3 h-2 rounded bg-red-500"/><span>Negative</span></div>
              <span className="ml-auto">{data.narratives_analysed} narratives analysed · {data.period_days}d window</span>
            </div>
          </div>

          {/* Narrative breakdowns with full analyst interpretation */}
          {(data.narrative_polarisation || []).length > 0 ? (
            <div className="space-y-4">
              {data.narrative_polarisation.map((n: any) => (
                <div key={n.narrative} className={`border rounded-2xl p-6 ${POL_BG(n.polarisation_score)}`}>
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-base font-bold text-white mb-1">{n.narrative}</h3>
                      <div className="flex items-center gap-3">
                        <span className={`text-xs font-bold ${POL_COLOR(n.polarisation_score)}`}>
                          Polarisation: {n.polarisation_score}/100
                        </span>
                        <span className={`text-xs font-bold ${STAB_COLOR(n.stability)}`}>{n.stability}</span>
                        <span className={`text-xs ${CONF_COLOR(n.confidence_level)}`}>{n.confidence_level} confidence</span>
                        <span className="text-xs text-white/30">{n.evidence_count} posts analysed</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs shrink-0 ml-4">
                      {!n.is_narrative_specific && (
                        <span className="bg-amber-900/30 border border-amber-700/30 text-amber-400 px-2 py-0.5 rounded-full">Low data</span>
                      )}
                    </div>
                  </div>

                  {/* Sentiment bar */}
                  <div className="mb-4">
                    <SentimentBar
                      pos={n.sentiment_distribution?.positive || 0}
                      neg={n.sentiment_distribution?.negative || 0}
                      neu={n.sentiment_distribution?.neutral || 0}
                    />
                  </div>

                  {/* Analyst interpretation */}
                  <div className="space-y-3">
                    {n.what_happened && (
                      <div className="flex items-start gap-3">
                        <span className="text-xs font-bold text-white/50 w-28 shrink-0 uppercase tracking-wide mt-0.5">What Happened</span>
                        <p className="text-sm text-white/80 leading-relaxed">{n.what_happened}</p>
                      </div>
                    )}
                    {n.why_it_matters && (
                      <div className="flex items-start gap-3">
                        <span className="text-xs font-bold text-white/50 w-28 shrink-0 uppercase tracking-wide mt-0.5">Why It Matters</span>
                        <p className="text-sm text-white/80 leading-relaxed">{n.why_it_matters}</p>
                      </div>
                    )}
                    {n.monitor && (
                      <div className="flex items-start gap-3">
                        <Eye size={12} className="text-purple-400 shrink-0 mt-0.5"/>
                        <p className="text-xs text-white/60 leading-relaxed italic">{n.monitor}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
              <p className="text-white/60 text-sm mb-2">Building narrative-specific polarisation baseline</p>
              <p className="text-white/40 text-xs">Reliable analysis requires 7-14 days of data accumulation per narrative. Check back as the platform matures.</p>
            </div>
          )}

          {/* Most polarised vs consensus */}
          {(data.most_polarised || []).length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-slate-900 border border-red-700/20 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle size={14} className="text-red-400"/>
                  <h3 className="text-xs font-bold text-red-400 uppercase tracking-wide">Most Polarised Narratives</h3>
                </div>
                {data.most_polarised.map((n: any) => (
                  <div key={n.narrative} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                    <span className="text-sm text-white">{n.narrative}</span>
                    <span className={`text-xs font-bold ${POL_COLOR(n.polarisation_score)}`}>{n.polarisation_score}/100</span>
                  </div>
                ))}
              </div>
              {(data.most_consensus || []).length > 0 && (
                <div className="bg-slate-900 border border-teal-700/20 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle size={14} className="text-teal-400"/>
                    <h3 className="text-xs font-bold text-teal-400 uppercase tracking-wide">Strongest Consensus</h3>
                  </div>
                  {data.most_consensus.map((n: any) => (
                    <div key={n.narrative} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                      <span className="text-sm text-white">{n.narrative}</span>
                      <span className="text-xs font-bold text-teal-400">{n.consensus_score}/100</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
