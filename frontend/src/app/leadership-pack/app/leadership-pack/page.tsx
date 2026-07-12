"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import {
  Shield, TrendingUp, TrendingDown, Minus, AlertTriangle,
  Lightbulb, Clock, CheckCircle, Download, BarChart2, Globe,
  Target, FileText, Star, List, Brain
} from "lucide-react";

const CONF = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-white";
const CONF_BG = (c: string) => c === "High" ? "bg-teal-500/20 text-teal-300 border-teal-700/30" : c === "Medium" ? "bg-amber-500/20 text-amber-300 border-amber-700/30" : "bg-slate-700 text-white border-slate-600";
const RISK_STYLE = (l: string) => l === "Critical" ? "border-red-600 bg-red-600/10 text-red-400" : l === "Warning" ? "border-orange-500 bg-orange-500/8 text-orange-400" : l === "Watch" ? "border-amber-500/50 bg-amber-500/5 text-amber-400" : "border-blue-500/30 bg-blue-500/5 text-blue-400";
const RANK_BG = (r: string) => r === "High" ? "bg-teal-500/20 text-teal-300" : r === "Medium" ? "bg-blue-500/20 text-blue-300" : "bg-slate-700 text-white";
const MOM = (d: string) => d === "rising" ? <TrendingUp size={13} className="text-teal-400"/> : d === "falling" ? <TrendingDown size={13} className="text-red-400"/> : <Minus size={13} className="text-white"/>;
const SENT = (s: string) => s === "positive" ? "text-teal-400" : s === "negative" ? "text-red-400" : "text-white";
const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";

function PageHeader({ num, title, subtitle }: { num: string; title: string; subtitle?: string }) {
  return (
    <div className="flex items-center gap-3 mb-6 pb-3 border-b border-slate-700">
      <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">{num}</div>
      <div>
        <h2 className="text-lg font-bold text-white">{title}</h2>
        {subtitle && <p className="text-xs text-white mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function NarrativeCard({ a }: { a: any }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white text-base">{a.narrative}</span>
          <span className={"text-xs px-2 py-0.5 rounded-full border " + CONF_BG(a.confidence_label)}>{a.confidence_label}</span>
          <span className={"text-xs px-2 py-0.5 rounded-full " + (a.strategic_importance === "High" ? "bg-purple-500/20 text-purple-300" : "bg-slate-700 text-white")}>{a.strategic_importance} priority</span>
        </div>
        <div className="flex items-center gap-3">
          {MOM(a.momentum_direction)}
          <span className={"text-xs font-medium " + SENT(a.sentiment_label)}>{a.sentiment_label}</span>
          <span className="text-lg font-bold text-white tabular-nums">{a.share_of_voice}%</span>
        </div>
      </div>
      <div className="space-y-3">
        {[
          { label: "What happened", text: a.what_happened, color: "text-blue-400" },
          { label: "Why it matters", text: a.why_it_matters, color: "text-white" },
          { label: "What changed", text: a.what_changed, color: "text-white" },
          { label: "Implication", text: a.implication, color: "text-amber-400" },
          { label: "Leadership action", text: a.leadership_considerations, color: "text-white" },
        ].map(({ label, text, color }) => text ? (
          <div key={label} className="flex items-start gap-3">
            <span className={"text-xs font-bold w-28 shrink-0 mt-0.5 uppercase tracking-wide " + color}>{label}</span>
            <p className="text-sm text-white leading-relaxed flex-1" dangerouslySetInnerHTML={{ __html: b(text) }} />
          </div>
        ) : null)}
        <div className="flex items-start gap-3 pt-2 border-t border-slate-700/50">
          <span className="text-xs font-bold text-blue-300 w-28 shrink-0 mt-0.5 uppercase tracking-wide">Monitor</span>
          <p className="text-xs text-white leading-relaxed flex-1">{a.monitoring_priority}</p>
        </div>
      </div>
    </div>
  );
}

export default function LeadershipPackPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [actions, setActions] = useState<any>(null);

  useEffect(() => {
    setLoading(true);
    api.get("/national-pulse/executive-actions?days=" + days)
      .then(r => setActions(r.data))
      .catch(() => {});
    api.get("/leadership-pack/?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const downloadTxt = () => {
    if (!data) return;
    const lines = [
      "NATIONAL & DIASPORA INTELLIGENCE PLATFORM (NDIP)",
      "LEADERSHIP INTELLIGENCE PACK",
      "Powered by RTIFN",
      "Generated: " + new Date(data.generated_at).toLocaleString(),
      "Analysis period: " + data.period_days + " days",
      "=".repeat(60),
      "PAGE 1 — EXECUTIVE SUMMARY",
      data.executive_summary,
      "",
      "NATIONAL CONTEXT",
      data.national_context,
      "",
      "WHAT CHANGED",
      ...(data.significant_changes || []).map((c: string) => "• " + c.replace(/\*\*/g, "")),
      "",
      "COMPARATIVE INTELLIGENCE",
      ...(data.comparative_intelligence || []).map((c: string) => "• " + c.replace(/\*\*/g, "")),
      "=".repeat(60),
      "PAGE 2 — STRATEGIC NARRATIVE ASSESSMENT",
      ...(data.narrative_assessments || []).map((a: any) => [
        "",
        a.narrative.toUpperCase() + " [" + a.share_of_voice + "% | " + a.sentiment_label + " | " + a.confidence_label + "]",
        "What happened: " + (a.what_happened || "").replace(/\*\*/g, ""),
        "Why it matters: " + (a.why_it_matters || ""),
        "What changed: " + (a.what_changed || "").replace(/\*\*/g, ""),
        "Implication: " + (a.implication || "").replace(/\*\*/g, ""),
        "Leadership action: " + (a.leadership_considerations || ""),
        "Monitor: " + (a.monitoring_priority || ""),
      ].join("\n")),
      "=".repeat(60),
      "PAGE 3 — STRATEGIC RISKS",
      ...(data.risks || []).map((r: any) => "[" + r.level + "] " + r.title + "\n" + r.detail.replace(/\*\*/g, "") + "\nAction: " + r.action),
      "=".repeat(60),
      "PAGE 4 — STRATEGIC OPPORTUNITIES",
      ...(data.opportunities || []).map((o: any) => "[" + o.rank + "] " + o.title + "\n" + o.detail.replace(/\*\*/g, "") + "\nAction: " + o.action),
      "=".repeat(60),
      "PAGE 5 — OUTLOOK",
      "7-Day: " + (data.outlook?.["7_day"] || "").replace(/\*\*/g, ""),
      "14-Day: " + (data.outlook?.["14_day"] || "").replace(/\*\*/g, ""),
      "30-Day: " + (data.outlook?.["30_day"] || "").replace(/\*\*/g, ""),
      "",
      "CONFIDENCE STATEMENT",
      (data.confidence_statement?.summary || ""),
      ...(data.confidence_statement?.limitations || []).map((l: string) => "• " + l),
      "=".repeat(60),
      "NDIP — Powered by RTIFN · Not for public distribution",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "NDIP-Leadership-Pack-" + new Date().toISOString().slice(0,10) + ".txt";
    a.click();
  };

  const downloadPdf = async () => {
    const token = localStorage.getItem("agora_token");
    const res = await fetch(`http://localhost:8000/export/leadership-pack.pdf?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `NDIP-Leadership-Pack-${new Date().toISOString().slice(0,10)}.pdf`;
    a.click();
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Star size={20} className="text-amber-400"/>
            <h1 className="text-3xl font-bold text-white">Leadership Intelligence Pack</h1>
          </div>
          <p className="text-white text-sm">Board-ready briefing · NDIP v5.4 · Powered by RTIFN</p>
          <p className="text-xs text-white mt-1 italic">Understanding Nigeria. Understanding the Diaspora.</p>
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
          <button onClick={downloadTxt} className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg px-3 py-2 text-sm transition-colors">
            <Download size={13} />.txt
          </button>
          <button onClick={downloadPdf} className="flex items-center gap-2 bg-blue-700 hover:bg-blue-600 text-white rounded-lg px-4 py-2 text-sm transition-colors font-medium">
            <Download size={13} />Download PDF
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white text-sm">Preparing leadership intelligence pack...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white">Unable to load. Please try again.</p></div>
      ) : (
        <div className="space-y-8">
          {/* PAGE 1 — Executive Summary */}
          <div className="bg-gradient-to-br from-blue-900/40 to-slate-900 border border-blue-700/40 rounded-2xl p-7">
            <div className="flex items-center justify-between mb-5">
              <PageHeader num="1" title="Executive Summary" subtitle="What happened · Why it matters · Key changes"/>
              <span className="text-xs text-white">{new Date(data.generated_at).toLocaleString()} · {data.period_days}d window</span>
            </div>
            <p className="text-white text-base leading-relaxed mb-5">{data.executive_summary}</p>
            {data.national_context && (
              <div className="bg-blue-900/20 border border-blue-700/20 rounded-xl p-4 mb-5">
                <p className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-2">National Context</p>
                <p className="text-white text-sm leading-relaxed">{data.national_context}</p>
              </div>
            )}
            {(data.significant_changes || []).length > 0 && (
              <div className="mb-5">
                <p className="text-xs font-bold text-white uppercase tracking-wider mb-2">Key Changes</p>
                <div className="space-y-2">
                  {data.significant_changes.map((c: string, i: number) => (
                    <div key={i} className="flex items-start gap-2">
                      <TrendingUp size={13} className="text-teal-400 mt-1 shrink-0"/>
                      <p className="text-sm text-white">{c}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* Narrative competition */}
            {data.competition_analysis?.competition_summary && (
              <div className="bg-slate-800/50 rounded-xl p-4 mb-5">
                <p className="text-xs font-bold text-purple-400 uppercase tracking-wider mb-2">Narrative Competition</p>
                <p className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{__html: b(data.competition_analysis.competition_summary)}}/>
                <div className="flex items-center gap-4 mt-3">
                  <span className="text-xs text-white">Attention concentration: <strong className="text-white">{data.competition_analysis.concentration_label}</strong> ({data.competition_analysis.concentration_score}%)</span>
                </div>
              </div>
            )}
            {(data.comparative_intelligence || []).length > 0 && (
              <div>
                <p className="text-xs font-bold text-white uppercase tracking-wider mb-2">Comparative Intelligence</p>
                <div className="space-y-2">
                  {data.comparative_intelligence.map((c: string, i: number) => (
                    <p key={i} className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{__html: b(c)}}/>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* LEADERSHIP WATCHLIST */}
          {data.watchlist && data.watchlist.items?.length > 0 && (
            <div className={`border rounded-2xl p-7 ${data.watchlist.critical_count > 0 ? "bg-red-900/20 border-red-700/40" : data.watchlist.high_count > 0 ? "bg-orange-900/20 border-orange-700/30" : "bg-slate-900 border-slate-800"}`}>
              <div className="flex items-center gap-2 mb-4">
                <List size={18} className="text-amber-400"/>
                <h2 className="text-base font-bold text-white">Leadership Watchlist</h2>
                <span className="text-xs text-white ml-1">What requires attention now</span>
                {data.watchlist.critical_count > 0 && <span className="ml-auto text-xs font-bold text-red-400 bg-red-900/30 border border-red-700/30 px-2 py-0.5 rounded-full">{data.watchlist.critical_count} Critical</span>}
                {data.watchlist.high_count > 0 && <span className={`${data.watchlist.critical_count > 0 ? "" : "ml-auto"} text-xs font-bold text-orange-400 bg-orange-900/30 border border-orange-700/30 px-2 py-0.5 rounded-full`}>{data.watchlist.high_count} High</span>}
              </div>
              <p className="text-white text-sm leading-relaxed mb-4">{data.watchlist.summary}</p>
              <div className="space-y-3">
                {data.watchlist.items.slice(0,5).map((item: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-700/50">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 mt-0.5 ${item.priority === "Critical" ? "bg-red-900/40 text-red-400 border border-red-700/30" : item.priority === "High" ? "bg-orange-900/40 text-orange-400 border border-orange-700/30" : item.priority === "Medium" ? "bg-amber-900/40 text-amber-400 border border-amber-700/30" : "bg-slate-700 text-white border-slate-600"}`}>{item.priority}</span>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-white mb-1" dangerouslySetInnerHTML={{__html: b(item.title)}}/>
                      <p className="text-xs text-white">{item.why_it_matters.slice(0,120)}...</p>
                    </div>
                    <span className={`text-xs font-bold shrink-0 px-2 py-0.5 rounded-full border ${item.executive_action === "Escalate" ? "bg-red-500/20 text-red-300 border-red-700/30" : item.executive_action === "Act" ? "bg-orange-500/20 text-orange-300 border-orange-700/30" : item.executive_action === "Prepare" ? "bg-amber-500/20 text-amber-300 border-amber-700/30" : "bg-slate-700 text-white border-slate-600"}`}>{item.executive_action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* EXECUTIVE ACTIONS */}
          {actions && actions.actions?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle size={18} className="text-teal-400"/>
                <h2 className="text-base font-bold text-white">Executive Actions</h2>
                <span className="text-xs text-white/50 ml-1">Recommended leadership actions this period</span>
              </div>
              <p className="text-sm text-white/70 mb-4">{actions.summary}</p>
              <div className="space-y-3">
                {actions.actions.slice(0,4).map((a: any, i: number) => (
                  <div key={i} className={`border rounded-xl p-4 ${a.category === "Escalate" ? "border-red-600 bg-red-600/10" : a.category === "Act" ? "border-orange-500 bg-orange-500/8" : a.category === "Prepare" ? "border-amber-500/40 bg-amber-500/5" : "border-slate-700 bg-slate-800/40"}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs font-bold uppercase ${a.category === "Escalate" ? "text-red-400" : a.category === "Act" ? "text-orange-400" : a.category === "Prepare" ? "text-amber-400" : "text-white/60"}`}>{a.category}</span>
                      <span className="text-xs text-white/40 ml-auto">{a.source}</span>
                    </div>
                    <p className="text-sm font-semibold text-white mb-1">{a.title}</p>
                    <p className="text-xs text-white/70 leading-relaxed mb-1">{a.recommended_action}</p>
                    <p className="text-xs text-white/40 italic">Expected: {a.expected_outcome}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PAGE 2 — Strategic Narrative Assessment */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
            <PageHeader num="2" title="Strategic Narrative Assessment" subtitle="Current position · Direction · Sentiment · Implications"/>
            {(data.narrative_assessments || []).map((a: any) => <NarrativeCard key={a.narrative} a={a}/>)}
          </div>

          {/* PAGE 3 — Strategic Risks */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
            <PageHeader num="3" title="Strategic Risks" subtitle="Prioritised · High / Medium / Low"/>
            {!(data.risks || []).filter((r: any) => r.level !== "Information").length ? (
              <div className="flex items-center gap-2 text-teal-400 p-4 bg-teal-900/10 border border-teal-700/20 rounded-xl">
                <CheckCircle size={16}/><span className="text-white font-medium">No critical or warning-level risks identified this period.</span>
              </div>
            ) : (
              <div className="space-y-4">
                {(data.risks || []).sort((a: any, b: any) => (a.level_order||3)-(b.level_order||3)).map((r: any, i: number) => (
                  <div key={i} className={"border rounded-xl p-5 " + RISK_STYLE(r.level)}>
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle size={14}/>
                      <span className="text-xs font-bold uppercase">{r.level}</span>
                      <span className={"ml-auto text-xs " + CONF(r.confidence_label)}>{r.confidence_label} confidence</span>
                    </div>
                    <p className="text-base font-bold text-white mb-2" dangerouslySetInnerHTML={{__html: b(r.title)}}/>
                    <p className="text-sm text-white leading-relaxed mb-3" dangerouslySetInnerHTML={{__html: b(r.detail)}}/>
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <p className="text-xs font-bold text-white mb-1">Recommended Action</p>
                      <p className="text-sm text-white">{r.action}</p>
                    </div>
                    {r.evidence_count > 0 && <p className="text-xs text-white mt-2">Based on {r.evidence_count.toLocaleString()} records · {r.rationale}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* PAGE 4 — Strategic Opportunities */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
            <PageHeader num="4" title="Strategic Opportunities" subtitle="Prioritised · High / Medium / Low"/>
            {!(data.opportunities || []).length ? (
              <p className="text-white">No specific opportunities identified this period.</p>
            ) : (
              <div className="space-y-4">
                {(data.opportunities || []).map((o: any, i: number) => (
                  <div key={i} className="border border-slate-700 bg-slate-800/30 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={"text-xs font-bold px-2 py-1 rounded-full " + RANK_BG(o.rank)}>{o.rank} Priority</span>
                      <span className={"ml-auto text-xs " + CONF(o.confidence_label)}>{o.confidence_label} confidence</span>
                    </div>
                    <p className="text-base font-bold text-white mb-2" dangerouslySetInnerHTML={{__html: b(o.title)}}/>
                    <p className="text-sm text-white leading-relaxed mb-3" dangerouslySetInnerHTML={{__html: b(o.detail)}}/>
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <p className="text-xs font-bold text-white mb-1">Recommended Action</p>
                      <p className="text-sm text-white">{o.action}</p>
                    </div>
                    {o.rationale && <p className="text-xs text-white mt-2">{o.rationale}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* DECISION SUPPORT PERFORMANCE — V5.6 Learning Loop */}
          {data.decision_support_performance && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={18} className="text-purple-400"/>
                <h2 className="text-base font-bold text-white">Decision Support Performance</h2>
                <span className="text-xs text-white/50 ml-1">NDIP measures its own recommendation accuracy</span>
              </div>
              <p className="text-sm text-white/70 mb-5">{data.decision_support_performance.narrative_summary}</p>
              <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
                {[
                  { label: "Generated", value: data.decision_support_performance.recommendations_generated, color: "text-white" },
                  { label: "Evaluated", value: data.decision_support_performance.recommendations_evaluated, color: "text-white" },
                  { label: "Validated", value: data.decision_support_performance.validated, color: "text-teal-400" },
                  { label: "Partially Validated", value: data.decision_support_performance.partially_validated, color: "text-amber-400" },
                  { label: "Invalidated", value: data.decision_support_performance.invalidated, color: "text-red-400" },
                  { label: "Avg Accuracy", value: data.decision_support_performance.average_accuracy !== null ? data.decision_support_performance.average_accuracy + "%" : "N/A", color: "text-purple-400" },
                ].map((s, i) => (
                  <div key={i} className="bg-slate-800/50 rounded-xl p-4 text-center">
                    <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-white/50 mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* INTELLIGENCE PERFORMANCE — V5.8 Platform-Wide Learning */}
          {data.intelligence_performance && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-2">
                <Brain size={18} className="text-purple-400"/>
                <h2 className="text-base font-bold text-white">Intelligence Performance</h2>
                <span className="text-xs text-white/50 ml-1">Platform Learning Score · Forecast accuracy · Lessons learned</span>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-5">
                {[
                  { label: "Platform Learning Score", value: data.intelligence_performance.platform_learning_score !== null ? data.intelligence_performance.platform_learning_score + "%" : "N/A", color: "text-purple-400" },
                  { label: "Recommendation Accuracy", value: data.intelligence_performance.decision_quality_metrics?.average_accuracy !== null && data.intelligence_performance.decision_quality_metrics?.average_accuracy !== undefined ? data.intelligence_performance.decision_quality_metrics.average_accuracy + "%" : "N/A", color: "text-white" },
                  { label: "Forecast Accuracy", value: data.intelligence_performance.decision_quality_metrics?.forecast_accuracy !== null && data.intelligence_performance.decision_quality_metrics?.forecast_accuracy !== undefined ? data.intelligence_performance.decision_quality_metrics.forecast_accuracy + "%" : "N/A", color: "text-white" },
                  { label: "Outlook Accuracy", value: data.intelligence_performance.decision_quality_metrics?.outlook_accuracy !== null && data.intelligence_performance.decision_quality_metrics?.outlook_accuracy !== undefined ? data.intelligence_performance.decision_quality_metrics.outlook_accuracy + "%" : "N/A", color: "text-white" },
                  { label: "Recommendations Improved", value: data.intelligence_performance.recommendations_improved_count, color: "text-teal-400" },
                ].map((s, i) => (
                  <div key={i} className="bg-slate-800/50 rounded-xl p-4 text-center">
                    <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-white/50 mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
              {data.intelligence_performance.lessons_learned?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-white/60 uppercase tracking-wide mb-2">Lessons Learned</p>
                  <div className="space-y-2">
                    {data.intelligence_performance.lessons_learned.slice(0,3).map((l: any, i: number) => (
                      <div key={i} className="flex items-start gap-2 p-3 bg-slate-800/40 rounded-lg">
                        <Lightbulb size={12} className="text-amber-400 shrink-0 mt-0.5"/>
                        <p className="text-xs text-white/80 leading-relaxed">{l.lesson}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* PAGE 5 — Outlook + Confidence */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
            <PageHeader num="5" title="Outlook & Confidence" subtitle="Evidence · Source diversity · Data quality · Limitations"/>
            {/* Outlook */}
            <div className="space-y-4 mb-8">
              {[
                {key:"7_day", label:"7-Day Outlook", icon: Clock},
                {key:"14_day", label:"14-Day Outlook", icon: Clock},
                {key:"30_day", label:"30-Day Outlook", icon: Clock},
              ].map(({key, label, icon: Icon}) => (
                <div key={key} className="flex items-start gap-4 p-4 bg-slate-800/50 rounded-xl">
                  <div className="shrink-0 mt-0.5">
                    <Icon size={16} className="text-blue-400"/>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-white uppercase tracking-wider mb-1">{label}</p>
                    <p className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{__html: b(data.outlook?.[key] || "")}}/>
                  </div>
                </div>
              ))}
              {data.outlook?.outlook_basis && (
                <p className="text-xs text-white italic">{data.outlook.outlook_basis}</p>
              )}
            </div>
            {/* Confidence */}
            {data.confidence_statement && (
              <>
                <div className="border-t border-slate-700 pt-6">
                  <p className="text-sm font-bold text-white mb-4">Confidence Statement</p>
                  <p className="text-sm text-white leading-relaxed mb-4" dangerouslySetInnerHTML={{__html: b(data.confidence_statement.summary)}}/>
                  <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
                    {[
                      {label:"Overall", value: data.confidence_statement.overall_rating || "High", col: true, val: data.confidence_statement.overall_rating || "High"},
                      {label:"Sources", value: data.confidence_statement.source_coverage},
                      {label:"Evidence", value: data.confidence_statement.evidence_volume},
                      {label:"NLP Rate", value: data.confidence_statement.nlp_success_rate},
                      {label:"Diversity", value: data.confidence_statement.source_diversity, col: true, val: data.confidence_statement.source_diversity},
                    ].map((item, i) => (
                      <div key={i} className="bg-slate-800 rounded-lg p-3 text-center">
                        <p className={"text-sm font-bold " + (item.col ? CONF(item.val!) : "text-white")}>{item.value || "—"}</p>
                        <p className="text-xs text-white mt-0.5">{item.label}</p>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-1.5">
                    {(data.confidence_statement.limitations || []).map((l: string, i: number) => (
                      <div key={i} className="flex items-start gap-2">
                        <AlertTriangle size={11} className="text-amber-400 mt-0.5 shrink-0"/>
                        <p className="text-xs text-white">{l}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* V6.0/V6.1 Phase G/H — Stakeholder & Opportunity sections. The
              backend has returned these fields since V6.0, but they were
              not previously rendered on this page. */}
          {(data.key_stakeholders || []).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <Star size={18} className="text-amber-400"/>
                <h2 className="text-base font-bold text-white">Top Strategic Stakeholders</h2>
                <span className="text-xs text-white ml-1">Ranked by strategic relevance</span>
              </div>
              <div className="space-y-2">
                {data.key_stakeholders.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <div>
                      <span className="text-sm text-white font-medium">{s.name}</span>
                      <span className="text-xs text-white ml-2">{(s.category || "").replace(/_/g, " ")}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-white">
                      <span>{s.mention_count} mentions</span>
                      <span className="font-bold text-teal-400">{s.strategic_relevance_score}</span>
                      <span className={
                        s.monitoring_priority === "Critical" ? "text-red-400 font-bold" :
                        s.monitoring_priority === "High" ? "text-amber-400 font-bold" : "text-white"
                      }>{s.monitoring_priority}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(data.stakeholder_influence_summary || []).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <Brain size={18} className="text-purple-400"/>
                <h2 className="text-base font-bold text-white">Stakeholder Influence Summary</h2>
                <span className="text-xs text-white ml-1">Composite index — Influence, Momentum, Narrative Impact, Opportunity Relevance, Engagement Priority, Relationship Strength</span>
              </div>
              <div className="space-y-2">
                {data.stakeholder_influence_summary.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <span className="text-sm text-white font-medium">{s.name}</span>
                    <div className="flex items-center gap-3 text-xs text-white">
                      <span>{s.composite_index}</span>
                      <span className={
                        s.influence_level === "Critical" ? "text-red-400 font-bold" :
                        s.influence_level === "High" ? "text-amber-400 font-bold" :
                        s.influence_level === "Medium" ? "text-teal-400 font-bold" : "text-white"
                      }>{s.influence_level}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(data.emerging_stakeholders || []).length > 0 && (
            <div className="bg-teal-900/10 border border-teal-700/30 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <TrendingUp size={18} className="text-teal-400"/>
                <h2 className="text-base font-bold text-white">Emerging Stakeholders</h2>
                <span className="text-xs text-white ml-1">Rising momentum, not yet in the top influence tier</span>
              </div>
              <div className="space-y-2">
                {data.emerging_stakeholders.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-900/40 rounded-lg">
                    <span className="text-sm text-white font-medium">{s.name}</span>
                    <span className="text-xs text-teal-400 font-bold">momentum {s.momentum_score}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(data.engagement_priorities || []).length > 0 && (
            <div className="bg-amber-900/10 border border-amber-700/30 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <AlertTriangle size={18} className="text-amber-400"/>
                <h2 className="text-base font-bold text-white">Recommended Engagement Priorities</h2>
                <span className="text-xs text-white ml-1">Who leadership should engage next</span>
              </div>
              <div className="space-y-2">
                {data.engagement_priorities.map((s: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-900/40 rounded-lg">
                    <span className="text-sm text-white font-medium">{s.name}</span>
                    <span className="text-xs text-white">{s.recent_activity}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(data.strategic_opportunities || []).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <Target size={18} className="text-teal-400"/>
                <h2 className="text-base font-bold text-white">Strategic Opportunities Watchlist</h2>
                <span className="text-xs text-white ml-1">Top opportunities this period</span>
              </div>
              <div className="space-y-3">
                {data.strategic_opportunities.map((o: any, i: number) => (
                  <div key={i} className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/30">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <span className="text-sm font-bold text-white">{o.title}</span>
                      <span className={
                        "text-xs font-bold px-2 py-1 rounded-lg border shrink-0 " +
                        (o.strategic_value === "Critical" ? "text-red-400 bg-red-900/20 border-red-700/30" :
                         o.strategic_value === "High" ? "text-amber-400 bg-amber-900/20 border-amber-700/30" :
                         "text-teal-400 bg-teal-900/20 border-teal-700/30")
                      }>{o.strategic_value}</span>
                    </div>
                    <p className="text-sm text-white leading-relaxed">{o.why_it_matters}</p>
                    {o.recommended_engagement && (
                      <p className="text-xs text-teal-400 mt-2"><strong>Action:</strong> {o.recommended_engagement}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.opportunity_pipeline && Object.keys(data.opportunity_pipeline).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <BarChart2 size={18} className="text-blue-400"/>
                <h2 className="text-base font-bold text-white">Opportunity Pipeline</h2>
              </div>
              <div className="flex items-center gap-4 overflow-x-auto">
                {["DETECTED", "ASSESSED", "ENGAGED", "IN_PROGRESS", "ADVANCED", "SECURED"].map((status) => (
                  <div key={status} className="text-center shrink-0 px-3">
                    <p className="text-xl font-bold text-white">{data.opportunity_pipeline[status] ?? 0}</p>
                    <p className="text-[10px] text-white mt-0.5 whitespace-nowrap">{status.replace(/_/g, " ")}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* GNEI Summary */}
          {data.gnei && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <Globe size={18} className="text-blue-400"/>
                  <h2 className="text-base font-bold text-white">Global Nigerian Engagement Index (GNEI)</h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-3xl font-bold text-white">{data.gnei.gnei_score}</span>
                  <span className="text-white">/100</span>
                  <span className="text-blue-400 font-semibold">{data.gnei.gnei_label}</span>
                </div>
              </div>
              <p className="text-white text-sm leading-relaxed mb-4">{data.gnei.assessment?.why_it_matters}</p>
              <p className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{__html: b(data.gnei.assessment?.what_changed || "")}}/>
            </div>
          )}

          {/* Trigger Attribution */}
          {(data.trigger_attributions || []).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-7">
              <div className="flex items-center gap-2 mb-5">
                <Brain size={18} className="text-purple-400"/>
                <h2 className="text-base font-bold text-white">What Is Driving Change?</h2>
                <span className="text-xs text-white ml-1">Trigger attribution analysis</span>
              </div>
              <div className="space-y-4">
                {data.trigger_attributions.map((t: any, i: number) => (
                  <div key={i} className="p-4 bg-purple-900/10 border border-purple-700/20 rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-bold text-white">{t.narrative}</span>
                      <span className="text-xs text-white bg-slate-800 px-2 py-0.5 rounded-full">+{t.momentum?.toFixed(0)}% momentum</span>
                      <span className={"ml-auto text-xs " + (t.trigger_confidence === "High" ? "text-teal-400" : t.trigger_confidence === "Medium" ? "text-amber-400" : "text-white")}>{t.trigger_confidence} confidence</span>
                    </div>
                    <p className="text-sm text-white leading-relaxed" dangerouslySetInnerHTML={{__html: b(t.trigger_summary)}}/>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-center py-4 border-t border-slate-800">
            <p className="text-xs text-white">National & Diaspora Intelligence Platform (NDIP) · Powered by RTIFN · {new Date(data.generated_at).toLocaleString()} · Not for public distribution</p>
          </div>
        </div>
      )}
    </div>
  );
}
