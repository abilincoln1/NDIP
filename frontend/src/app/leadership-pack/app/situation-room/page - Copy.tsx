"use client"; // v5.4
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import {
  AlertTriangle, TrendingUp, TrendingDown, CheckCircle,
  Eye, Lightbulb, Shield, Target, Clock, ChevronRight,
  BarChart2, Minus, Star, Database, Zap
} from "lucide-react";

const RISK_STYLES: Record<string,string> = {
  Critical:"border-red-600 bg-red-600/15", Warning:"border-orange-500 bg-orange-500/10",
  Watch:"border-amber-500 bg-amber-500/8", Information:"border-blue-500/40 bg-blue-500/5",
};
const RISK_COLORS: Record<string,string> = {
  Critical:"text-red-400", Warning:"text-orange-400", Watch:"text-amber-400", Information:"text-blue-400",
};
const CONF_COLORS: Record<string,string> = {
  High:"text-teal-400", Medium:"text-amber-400", Low:"text-slate-500",
};
const RANK_COLORS: Record<string,string> = {
  High:"border-teal-600 bg-teal-900/10", Medium:"border-blue-600/40 bg-blue-900/5", Low:"border-slate-700 bg-slate-800/30",
};
const RANK_BADGE: Record<string,string> = {
  High:"bg-teal-500/20 text-teal-300", Medium:"bg-blue-500/20 text-blue-300", Low:"bg-slate-700 text-slate-400",
};
const SENT_COLOR = (s:string) => s==="positive"?"text-teal-400":s==="negative"?"text-red-400":"text-slate-400";
const MOM_ICON = (d:string) => d==="rising"?<TrendingUp size={12} className="text-teal-400"/>:d==="falling"?<TrendingDown size={12} className="text-red-400"/>:<Minus size={12} className="text-slate-300"/>;

// Decision Support Summary panel — extracted to its own component so its
// useState/useEffect hooks live at a proper top level. Previously this was
// an inline IIFE `{(() => { useState(...); ... })()}` directly inside JSX,
// which violates React's Rules of Hooks (hooks must never be called inside
// a nested function) and intermittently crashed with React error #310
// ("rendered more hooks than during the previous render") whenever the
// page re-rendered for unrelated reasons (e.g. switching the days filter).
function DecisionSupportSummary() {
  const [ds, setDs] = useState<any>(null);
  useEffect(() => {
    api.get("/national-pulse/decision-support?days=7")
      .then(r => setDs(r.data)).catch(() => {});
  }, []);
  if (!ds?.decision_support_summary?.length) return null;
  return (
    <div className="bg-slate-800/60 border border-teal-700/20 rounded-xl p-5 mb-4">
      <p className="text-xs font-bold text-teal-400 uppercase tracking-wider mb-3">Leadership Decision Support Summary</p>
      <div className="space-y-2">
        {ds.decision_support_summary.map((b: string, i: number) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-teal-400 font-bold text-xs shrink-0 mt-0.5">{i+1}</span>
            <p className="text-sm text-white">{b}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SituationRoomPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/situation-room/?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const boldify = (text: string) => text?.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || "";

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Executive Situation Room</h1>
          <p className="text-white text-sm">Strategic intelligence platform · Plain English · RTIFN</p>
        </div>
        <div className="flex gap-2">
          {[{d:3,l:"3 days"},{d:7,l:"This week"},{d:14,l:"2 weeks"},{d:30,l:"This month"}].map(({d,l}) => (
            <button key={d} onClick={() => setDays(d)}
              className={"px-3 py-2 rounded-lg text-xs font-medium transition-colors " + (days===d?"bg-blue-600 text-white":"bg-slate-800 text-slate-400 hover:text-white")}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white text-sm">Preparing strategic intelligence...</p></div>
      ) : !data ? (
        <div className="card text-center py-16"><p className="text-slate-200">Unable to load. Please try again.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Executive Summary */}
          <div className="bg-gradient-to-r from-blue-900/40 to-slate-900 border border-blue-700/40 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"/>
              <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Executive Summary</span>
              <span className="ml-auto text-xs text-white">{new Date(data.generated_at).toLocaleString()}</span>
            </div>
            <p className="text-white text-base leading-relaxed">{data.executive_summary}</p>
          </div>

          {/* What Matters Most */}
          <div className="bg-amber-900/20 border border-amber-700/30 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <Target size={15} className="text-amber-400"/>
              <span className="text-xs font-bold text-amber-400 uppercase tracking-widest">What Matters Most Right Now</span>
            </div>
            <p className="text-white text-sm leading-relaxed" dangerouslySetInnerHTML={{__html: boldify(data.what_matters_most)}}/>
          </div>

          {/* Key Findings */}
          <div className="card">
            <div className="flex items-center gap-2 mb-5">
              <Eye size={18} className="text-blue-400"/>
              <h2 className="text-base font-bold text-white">Top 5 Key Findings</h2>
            </div>
            <div className="space-y-3">
              {(data.key_findings||[]).map((f:any,i:number) => {
                const text = typeof f==="string"?f:(f?.finding||"");
                const why = typeof f==="object"?f?.why_it_matters:null;
                const conf = typeof f==="object"?f?.confidence_label:null;
                const src = typeof f==="object"?f?.source_count:null;
                const ev = typeof f==="object"?f?.evidence_count:null;
                return (
                  <div key={i} className="p-4 bg-slate-800/50 rounded-xl">
                    <div className="flex items-start gap-3 mb-2">
                      <span className="text-blue-400 font-bold text-sm shrink-0 mt-0.5">{i+1}</span>
                      <p className="text-white text-sm leading-relaxed" dangerouslySetInnerHTML={{__html: boldify(text)}}/>
                    </div>
                    {why && <p className="text-xs text-white ml-6 mb-1">Why it matters: {why}</p>}
                    <div className="flex items-center gap-3 ml-6">
                      {conf && <span className={"text-xs font-semibold " + (CONF_COLORS[conf]||"text-slate-200")}>{conf} confidence</span>}
                      {src!=null && <span className="text-xs text-white">{src} source{src!==1?"s":""}</span>}
                      {ev!=null && ev>0 && <span className="text-xs text-white">{ev.toLocaleString()} data points</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Narrative Share of Voice */}
          {data.narrative_share_of_voice?.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-5">
                <BarChart2 size={18} className="text-purple-400"/>
                <h2 className="text-base font-bold text-white">Narrative Share of Voice</h2>
                <span className="text-xs text-white ml-1">Strategic themes in monitored discourse</span>
              </div>
              <div className="space-y-4">
                {data.narrative_share_of_voice.map((n:any) => (
                  <div key={n.narrative}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{n.narrative}</span>
                        <div className="flex items-center gap-1">{MOM_ICON(n.momentum_direction)}<span className="text-xs text-white">{n.momentum>0?"+":""}{n.momentum?.toFixed(0)}%</span></div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={"text-xs " + SENT_COLOR(n.sentiment_label)}>{n.sentiment_label}</span>
                        <span className="text-sm font-bold text-white tabular-nums">{n.share_of_voice}%</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-purple-500" style={{width: Math.min(n.share_of_voice*2,100)+"%"}}/>
                      </div>
                      <span className="text-xs text-white w-20 text-right">{n.count} mentions</span>
                    </div>
                    {n.strategic_insight && (
                      <p className="text-xs text-white leading-relaxed" dangerouslySetInnerHTML={{__html: boldify(n.strategic_insight)}}/>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Significant Changes */}
          {data.significant_changes?.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-4"><TrendingUp size={18} className="text-teal-400"/><h2 className="text-base font-bold text-white">What Changed</h2></div>
              <div className="space-y-2">
                {data.significant_changes.map((c:string,i:number) => (
                  <div key={i} className="flex items-start gap-2">
                    <ChevronRight size={14} className="text-teal-400 mt-1 shrink-0"/>
                    <p className="text-white text-sm">{c}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risks and Opportunities */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <Shield size={18} className="text-red-400"/>
                <h2 className="text-base font-bold text-white">Risks</h2>
                {!(data.risks||[]).filter((r:any)=>r.level!=="Information").length && (
                  <span className="ml-auto flex items-center gap-1 text-xs text-teal-400"><CheckCircle size={12}/>None critical</span>
                )}
              </div>
              {!(data.risks||[]).length ? <p className="text-white text-sm">No risks identified.</p> : (
                <div className="space-y-3">
                  {(data.risks||[]).sort((a:any,b:any)=>(a.level_order||3)-(b.level_order||3)).map((r:any,i:number) => (
                    <div key={i} className={"border rounded-xl p-4 " + (RISK_STYLES[r.level]||"border-slate-700 bg-slate-800/30")}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <AlertTriangle size={13} className={RISK_COLORS[r.level]||"text-slate-400"}/>
                        <span className={"text-xs font-bold uppercase " + (RISK_COLORS[r.level]||"text-slate-400")}>{r.level}</span>
                        <span className={"ml-auto text-xs " + (CONF_COLORS[r.confidence_label]||"text-slate-500")}>{r.confidence_label} confidence</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1" dangerouslySetInnerHTML={{__html: boldify(r.title)}}/>
                      <p className="text-xs text-white leading-relaxed mb-2" dangerouslySetInnerHTML={{__html: boldify(r.detail)}}/>
                      <p className="text-xs text-white"><span className="font-medium">Action:</span> {r.action}</p>
                      {r.evidence_count>0 && <p className="text-xs text-white mt-1">Based on {r.evidence_count.toLocaleString()} records</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <div className="flex items-center gap-2 mb-4"><Lightbulb size={18} className="text-teal-400"/><h2 className="text-base font-bold text-white">Opportunities</h2></div>
              {!(data.opportunities||[]).length ? <p className="text-white text-sm">No specific opportunities identified.</p> : (
                <div className="space-y-3">
                  {(data.opportunities||[]).map((o:any,i:number) => (
                    <div key={i} className={"border rounded-xl p-4 " + (RANK_COLORS[o.rank]||"border-slate-700 bg-slate-800/30")}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={"text-xs font-bold px-2 py-0.5 rounded-full " + (RANK_BADGE[o.rank]||"bg-slate-700 text-slate-400")}>{o.rank}</span>
                        <span className={"ml-auto text-xs " + (CONF_COLORS[o.confidence_label]||"text-slate-500")}>{o.confidence_label} confidence</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1" dangerouslySetInnerHTML={{__html: boldify(o.title)}}/>
                      <p className="text-xs text-white leading-relaxed mb-2" dangerouslySetInnerHTML={{__html: boldify(o.detail)}}/>
                      <p className="text-xs text-white"><span className="font-medium">Action:</span> {o.action}</p>
                      {o.evidence_count>0 && <p className="text-xs text-white mt-1">{o.rationale}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Emerging Topics */}
          {data.emerging_topics?.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-4"><TrendingUp size={18} className="text-purple-400"/><h2 className="text-base font-bold text-white">Emerging Topics</h2></div>
              <div className="space-y-3">
                {data.emerging_topics.map((t:any,i:number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-purple-900/10 border border-purple-700/20 rounded-xl">
                    <TrendingUp size={14} className="text-purple-400 mt-0.5 shrink-0"/>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-semibold text-white">{t.topic}</span>
                        <span className="text-xs text-white bg-slate-800 px-2 py-0.5 rounded-full">{t.category}</span>
                        <span className={"ml-auto text-xs font-bold " + (CONF_COLORS[t.confidence_label]||"text-purple-400")}>{t.confidence_label}</span>
                      </div>
                      <p className="text-xs text-white">{t.plain_english}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Coverage gaps */}
          {data.underrepresented_narratives?.length > 0 && (
            <div className="card border-amber-800/20">
              <div className="flex items-center gap-2 mb-3"><AlertTriangle size={15} className="text-amber-400"/><h2 className="text-sm font-bold text-white">Monitoring Coverage Alerts</h2></div>
              <div className="space-y-2">
                {data.underrepresented_narratives.map((u:any,i:number) => (
                  <div key={i} className="flex items-start gap-2 p-2 bg-amber-900/10 rounded-lg">
                    <ChevronRight size={12} className="text-amber-400 mt-1 shrink-0"/>
                    <p className="text-xs text-white">{u.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outlook */}
          <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-3"><Clock size={15} className="text-slate-200"/><span className="text-xs font-bold text-white uppercase tracking-widest">Trend Outlook</span></div>
            <p className="text-white text-sm leading-relaxed">{data.outlook}</p>
          </div>

          {/* Recommended Monitoring */}
          {data.recommended_monitoring?.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-bold text-white mb-3">Recommended Areas for Further Monitoring</h2>
              <div className="space-y-1.5">
                {data.recommended_monitoring.map((m:string,i:number) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0"/>
                    <p className="text-sm text-white">{m}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-center py-4 border-t border-slate-800">
            {/* Decision Support Summary */}
            <DecisionSupportSummary />
            <p className="text-xs text-white">National & Diaspora Intelligence Platform (NDIP) · Powered by RTIFN · {new Date(data.generated_at).toLocaleString()} · {data.period_days}-day window</p>
          </div>
        </div>
      )}
    </div>
  );
}
