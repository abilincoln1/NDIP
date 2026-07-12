"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import {
  Zap, TrendingUp, TrendingDown, Minus, AlertTriangle,
  Target, Clock, CheckCircle, ChevronRight, Star, Brain
} from "lucide-react";

const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";
const CONF = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-white";
const SENT = (s: string) => s === "positive" ? "text-teal-400" : s === "negative" ? "text-red-400" : "text-white";
const MOM_ICON = (d: string) => d === "rising" ? <TrendingUp size={13} className="text-teal-400"/> : d === "falling" ? <TrendingDown size={13} className="text-red-400"/> : <Minus size={13} className="text-white/50"/>;
const ACTION_STYLE: Record<string,string> = {
  Escalate: "border-red-600 bg-red-600/10 text-red-400",
  Act: "border-orange-500 bg-orange-500/8 text-orange-400",
  Prepare: "border-amber-500/50 bg-amber-500/5 text-amber-400",
  Monitor: "border-slate-600 bg-slate-800/40 text-white",
};
const URGENCY_COLOR: Record<string,string> = {
  Critical: "text-red-400", High: "text-orange-400", Medium: "text-amber-400", Low: "text-white"
};

function SectionHeader({ icon: Icon, color, label, sub }: any) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={16} className={color}/>
      <h2 className="text-sm font-bold text-white">{label}</h2>
      {sub && <span className="text-xs text-white/60">{sub}</span>}
    </div>
  );
}

export default function NationalPulsePage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/national-pulse/executive?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const ei = data?.executive_intelligence;

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Zap size={20} className="text-teal-400"/>
            <h1 className="text-3xl font-bold text-white">National Pulse</h1>
          </div>
          <p className="text-white/70 text-sm">Nigeria public discourse indicator · Executive intelligence · NDIP v5.4</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
            {[{d:3,l:"3d"},{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"}].map(({d,l}) => (
              <button key={d} onClick={() => setDays(d)}
                className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors " + (days===d?"bg-teal-600 text-white":"text-white/60 hover:text-white")}>
                {l}
              </button>
            ))}
          </div>
          {data && (
            <div className="bg-slate-800 border border-slate-700 rounded-xl px-5 py-3 text-center">
              <p className={`text-4xl font-bold ${data.pulse_score >= 70 ? "text-teal-400" : data.pulse_score >= 50 ? "text-amber-400" : "text-red-400"}`}>{data.pulse_score}</p>
              <p className="text-xs text-white/60 mt-1">National Pulse</p>
              <p className="text-xs text-white font-medium">{data.pulse_label}</p>
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white/60 text-sm">Generating executive intelligence...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white/60">Unable to load.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Confidence strip */}
          <div className="flex items-center gap-6 px-5 py-3 bg-slate-800/60 border border-slate-700 rounded-xl text-xs">
            <span className="text-white/50">{new Date(data.generated_at || ei?.generated_at).toLocaleString()} · {days}d window</span>
            <span className={CONF(data.confidence_label || "High")}>{data.confidence_label || "High"} confidence</span>
            <span className="text-white/60">{data.source_count || 12} sources</span>
            <span className="text-white/60">{data.total_records?.toLocaleString() || "—"} records</span>
            <span className="text-white/60">NLP: {data.nlp_rate || "—"}%</span>
          </div>

          {/* A. Executive Assessment */}
          {ei && (
            <div className="bg-gradient-to-br from-teal-900/30 to-slate-900 border border-teal-700/30 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Star size={16} className="text-teal-400"/>
                <span className="text-xs font-bold text-teal-400 uppercase tracking-widest">Executive Assessment</span>
              </div>
              <p className="text-white text-base leading-relaxed">{ei.executive_assessment}</p>
            </div>
          )}

          {/* Score grid */}
          <div className="grid grid-cols-4 gap-3">
            {(data.narrative_components || []).slice(0,4).map((n: any) => (
              <div key={n.narrative} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-white/60 truncate">{n.narrative}</span>
                  {MOM_ICON(n.momentum_direction)}
                </div>
                <p className="text-2xl font-bold text-white">{n.share_of_voice}%</p>
                <p className={`text-xs mt-1 ${SENT(n.sentiment_label)}`}>{n.sentiment_label}</p>
              </div>
            ))}
          </div>

          {/* B + C. Why It Matters + What Changed */}
          {ei && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <SectionHeader icon={Target} color="text-amber-400" label="Why It Matters" sub="Strategic significance"/>
                <div className="space-y-3">
                  {ei.why_it_matters.map((p: string, i: number) => (
                    <div key={i} className="flex items-start gap-2">
                      <ChevronRight size={13} className="text-amber-400 shrink-0 mt-0.5"/>
                      <p className="text-sm text-white leading-relaxed">{p}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <SectionHeader icon={TrendingUp} color="text-blue-400" label="What Changed" sub="Narrative + momentum shifts"/>
                <div className="space-y-3">
                  {ei.what_changed.map((c: any, i: number) => (
                    <div key={i} className="flex items-start gap-2 p-3 bg-slate-800/40 rounded-lg">
                      {MOM_ICON(c.direction)}
                      <p className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{__html: b(c.description)}}/>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Narrative share of voice */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={Brain} color="text-purple-400" label="Narrative Intelligence" sub="Share of voice · Sentiment · Momentum"/>
            <div className="space-y-2">
              {(data.narrative_components || []).map((n: any) => (
                <div key={n.narrative} className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-white">{n.narrative}</span>
                      {MOM_ICON(n.momentum_direction)}
                      <span className="text-xs text-white/50">{n.momentum > 0 ? "+" : ""}{n.momentum?.toFixed(0)}%</span>
                    </div>
                    <div className="bg-slate-700 rounded-full h-1">
                      <div className="bg-teal-500 h-1 rounded-full" style={{width: Math.min(n.share_of_voice * 2.5, 100) + "%"}}/>
                    </div>
                  </div>
                  <span className={`text-xs w-16 text-right ${SENT(n.sentiment_label)}`}>{n.sentiment_label}</span>
                  <span className="text-sm font-bold text-white tabular-nums w-10 text-right">{n.share_of_voice}%</span>
                  <span className={`text-xs w-16 text-right ${CONF(n.confidence_label)}`}>{n.confidence_label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* D. Leadership Watch Items + E. Recommended Actions */}
          {ei && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Watch Items */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <SectionHeader icon={AlertTriangle} color="text-amber-400" label="Leadership Watch Items" sub="Issues requiring monitoring"/>
                <div className="space-y-3">
                  {ei.leadership_watch_items.map((w: any, i: number) => (
                    <div key={i} className="p-3 bg-slate-800/40 rounded-xl border border-slate-700/50">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-bold ${URGENCY_COLOR[w.urgency]}`}>{w.urgency}</span>
                        <span className="text-xs text-white/50 ml-auto">{w.monitoring}</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1">{w.item}</p>
                      <p className="text-xs text-white/70 leading-relaxed">{w.reason}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Actions */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <SectionHeader icon={CheckCircle} color="text-teal-400" label="Recommended Actions" sub="Prioritised leadership actions"/>
                <div className="space-y-3">
                  {ei.recommended_actions.map((a: any, i: number) => (
                    <div key={i} className={`border rounded-xl p-4 ${ACTION_STYLE[a.priority] || "border-slate-700 bg-slate-800/40 text-white"}`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-bold uppercase tracking-wide">{a.priority}</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1">{a.action}</p>
                      <p className="text-xs text-white/80 leading-relaxed mb-2">{a.recommended_action}</p>
                      <p className="text-xs text-white/50 italic">Expected: {a.expected_outcome}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* F. Confidence */}
          <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
            <SectionHeader icon={CheckCircle} color="text-teal-400" label="Confidence Assessment"/>
            <div className="grid grid-cols-4 gap-4">
              {[
                {label: "Overall", value: data.confidence_label || "High", color: CONF(data.confidence_label || "High")},
                {label: "Sources", value: `${data.source_count || 12} active`, color: "text-white"},
                {label: "Evidence", value: `${data.total_records?.toLocaleString() || "—"}`, color: "text-white"},
                {label: "NLP Rate", value: `${data.nlp_rate || "—"}%`, color: "text-white"},
              ].map((item,i) => (
                <div key={i} className="text-center">
                  <p className={`text-lg font-bold ${item.color}`}>{item.value}</p>
                  <p className="text-xs text-white/50 mt-1">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Election Intelligence */}
          {data.election_intelligence && (
            <div className="bg-amber-900/10 border border-amber-700/20 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Clock size={15} className="text-amber-400"/>
                  <span className="text-sm font-bold text-white">Election Intelligence — Nigeria 2027</span>
                </div>
                <span className="text-amber-400 font-bold text-sm">{data.election_intelligence.days_remaining} days away</span>
              </div>
              <p className="text-xs text-white/70 leading-relaxed">{data.election_intelligence.summary}</p>
            </div>
          )}

          {/* Decision Support Summary */}
          {ei?.decision_support?.decision_support_summary?.length > 0 && (
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-600 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle size={16} className="text-teal-400"/>
                <h2 className="text-sm font-bold text-white">Leadership Decision Support Summary</h2>
                <span className="text-xs text-white/40 ml-1">If you read only this section</span>
              </div>
              <div className="space-y-2">
                {ei.decision_support.decision_support_summary.map((bullet: string, i: number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg">
                    <span className="text-teal-400 font-bold text-sm shrink-0">{i + 1}</span>
                    <p className="text-sm text-white leading-relaxed">{bullet}</p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-white/30 mt-3 italic">{ei.decision_support.safeguard_note}</p>
            </div>
          )}

          {/* Decision Support — Immediate Actions */}
          {ei?.decision_support?.immediate_actions?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={15} className="text-orange-400"/>
                <h2 className="text-sm font-bold text-white">Immediate Actions</h2>
                <span className="text-xs text-white/40">Within 7 days</span>
                <span className="ml-auto text-xs font-bold text-orange-400">{ei.decision_support.immediate_count} items</span>
              </div>
              <div className="space-y-3">
                {ei.decision_support.immediate_actions.map((a: any, i: number) => (
                  <div key={i} className={`border rounded-xl p-4 ${a.category === "ESCALATE" ? "border-red-600/50 bg-red-600/8" : a.category === "ENGAGE" ? "border-teal-500/40 bg-teal-500/5" : a.category === "INVESTIGATE" ? "border-purple-500/40 bg-purple-500/5" : "border-orange-500/40 bg-orange-500/5"}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs font-bold uppercase ${a.category === "ESCALATE" ? "text-red-400" : a.category === "ENGAGE" ? "text-teal-400" : a.category === "INVESTIGATE" ? "text-purple-400" : "text-orange-400"}`}>{a.category}</span>
                      <span className="text-xs text-white/40 ml-auto">{a.evidence}</span>
                    </div>
                    <p className="text-sm font-semibold text-white mb-1">{a.issue}</p>
                    <p className="text-xs text-white/70 leading-relaxed mb-2">{a.action}</p>
                    <p className="text-xs text-white/40 italic">Expected: {a.expected_outcome}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
