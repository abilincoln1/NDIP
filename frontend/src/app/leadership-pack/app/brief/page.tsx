"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import {
  FileText, Download, AlertTriangle, Lightbulb,
  TrendingUp, ChevronRight, Database, Shield, CheckCircle
} from "lucide-react";

function Section({ title, children, icon, accent }: {
  title: string; children: React.ReactNode; icon?: React.ReactNode; accent?: string;
}) {
  const border = accent === "blue" ? "border-blue-700/40" : accent === "amber" ? "border-amber-700/30" : "border-slate-800";
  return (
    <div className={"bg-slate-900 border rounded-xl p-5 " + border}>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">{title}</h2>
      </div>
      {children}
    </div>
  );
}

const CONF = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-slate-500";
const RANK_BADGE = (r: string) => r === "High" ? "bg-teal-500/20 text-teal-300" : r === "Medium" ? "bg-blue-500/20 text-blue-300" : "bg-slate-700 text-slate-400";
const RISK_COLOR = (l: string) => l === "Critical" ? "text-red-400" : l === "Warning" ? "text-orange-400" : l === "Watch" ? "text-amber-400" : "text-blue-400";

export default function BriefPage() {
  const [brief, setBrief] = useState<any>(null);
  const [period, setPeriod] = useState("weekly");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/situation-room/brief/" + period)
      .then(r => setBrief(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  const getText = (f: any) => typeof f === "string" ? f : (f?.finding || "");
  const boldify = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";

  const download = () => {
    if (!brief) return;
    const lines = [
      "NATIONAL & DIASPORA INTELLIGENCE PLATFORM (NDIP)",
      period.toUpperCase() + " INTELLIGENCE BRIEF",
      "Generated: " + new Date(brief.generated_at).toLocaleString(),
      "=".repeat(60),
      "EXECUTIVE SUMMARY",
      brief.executive_summary || "",
      "=".repeat(60),
      "KEY FINDINGS",
      ...(brief.key_findings || []).map((f: any, i: number) => (i + 1) + ". " + getText(f)),
      "=".repeat(60),
      "ENGAGEMENT OVERVIEW",
      brief.engagement_overview || "",
      brief.geographic_overview || "",
      "=".repeat(60),
      "NARRATIVE ANALYSIS",
      ...(brief.narrative_analysis || []).map((n: string) => "• " + n.replace(/\*\*/g, "")),
      "=".repeat(60),
      "SENTIMENT ANALYSIS",
      brief.sentiment_analysis || "",
      "=".repeat(60),
      "DIASPORA INTELLIGENCE",
      brief.diaspora_intelligence || "See Narrative Share of Voice for Diaspora coverage.",
      "=".repeat(60),
      "RISKS",
      ...(brief.risks || []).map((r: any) => "[" + r.level + "] " + r.title + ": " + r.detail + "\nAction: " + r.action),
      "=".repeat(60),
      "OPPORTUNITIES",
      ...(brief.opportunities || []).map((o: any) => "[" + o.rank + "] " + o.title + ": " + o.detail + "\nAction: " + o.action),
      "=".repeat(60),
      "EMERGING TOPICS",
      ...(brief.emerging_topics || []).map((t: any) => "• " + t.topic + " (" + t.category + "): " + t.plain_english),
      "=".repeat(60),
      "COVERAGE GAPS",
      ...(brief.coverage_gaps || ["No significant coverage gaps identified."]),
      "=".repeat(60),
      "CONFIDENCE ASSESSMENT",
      brief.source_quality ? "Overall confidence: " + brief.source_quality.overall_confidence_label + ". " + brief.source_quality.summary : "",
      "=".repeat(60),
      "DATA QUALITY",
      brief.data_quality ? "Processing rate: " + brief.data_quality.nlp_rate + "%. Topic quality: " + brief.data_quality.topic_quality_rate + "%." : "",
      "=".repeat(60),
      "WHAT TO WATCH NEXT",
      ...(brief.recommended_monitoring || []).map((m: string) => "• " + m),
      "=".repeat(60),
      "EXECUTIVE OUTLOOK",
      brief.outlook || "",
      "=".repeat(60),
      "RTIFN National & Diaspora Intelligence Platform (NDIP) — Aggregated, anonymised data only — Not for public distribution",
    ];
    const blob = new Blob([lines.join("\n\n")], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "RTIFN-" + period + "-brief-" + new Date().toISOString().slice(0, 10) + ".txt";
    a.click();
  };

  if (loading) return <div className="flex justify-center py-24"><Spinner /></div>;
  if (!brief) return <div className="card text-center py-12"><p className="text-slate-200">Unable to load brief.</p></div>;

  // Extract diaspora narrative
  const diasporaNarrative = (brief.narrative_share_of_voice || []).find((n: any) => n.narrative === "Diaspora");
  const coverageGaps = (brief.narrative_share_of_voice || [])
    .filter((n: any) => n.share_of_voice < 3)
    .map((n: any) => n.narrative);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Executive Intelligence Brief</h1>
          <p className="text-sm text-white mt-1">Plain-English intelligence for leadership · Under 5 minutes to read</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
            {["daily", "weekly", "monthly"].map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors capitalize " + (period === p ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200")}>
                {p}
              </button>
            ))}
          </div>
          <button onClick={download} className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg px-3 py-2 text-sm transition-colors">
            <Download size={14} />.txt
          </button>
          <button onClick={async () => {
            const token = localStorage.getItem("agora_token");
            const res = await fetch(`http://localhost:8000/export/brief.pdf?period=${period}`, {
              headers: { Authorization: `Bearer ${token}` }
            });
            const blob = await res.blob();
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `RTIFN-${period}-brief-${new Date().toISOString().slice(0,10)}.pdf`;
            a.click();
          }} className="flex items-center gap-2 bg-blue-700 hover:bg-blue-600 text-white rounded-lg px-3 py-2 text-sm transition-colors">
            <Download size={14} />PDF
          </button>
        </div>
      </div>

      <div className="space-y-5">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-900/30 to-slate-900 border border-blue-700/30 rounded-2xl p-5 flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 rounded-lg"><FileText size={20} className="text-blue-400" /></div>
          <div className="flex-1">
            <p className="font-bold text-white capitalize">{period} Intelligence Brief · RTIFN National & Diaspora Intelligence Platform (NDIP)</p>
            <p className="text-xs text-white">{new Date(brief.generated_at).toLocaleString()} · {brief.period_days}-day analysis window</p>
          </div>
          {brief.source_quality && (
            <div className="text-right">
              <p className={"text-sm font-bold " + CONF(brief.source_quality.overall_confidence_label)}>
                {brief.source_quality.overall_confidence_label} Confidence
              </p>
              <p className="text-xs text-white">{brief.source_quality.source_count} sources · {brief.source_quality.total_records} records</p>
            </div>
          )}
        </div>

        {/* Executive Summary */}
        <Section title="Executive Summary" accent="blue">
          <p className="text-white leading-relaxed text-sm">{brief.executive_summary}</p>
        </Section>

        {/* Key Findings */}
        <Section title="Key Findings">
          <ol className="space-y-4">
            {(brief.key_findings || []).map((f: any, i: number) => (
              <li key={i} className="flex items-start gap-3">
                <span className="text-blue-400 font-bold shrink-0 text-sm">{i + 1}.</span>
                <div>
                  <p className="text-white text-sm leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: boldify(getText(f)) }} />
                  {f?.why_it_matters && <p className="text-xs text-white mt-1">Why it matters: {f.why_it_matters}</p>}
                  {f?.confidence_label && (
                    <span className={"text-xs mt-1 " + CONF(f.confidence_label)}>{f.confidence_label} confidence</span>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Section>

        {/* Major Narrative Shifts */}
        {(brief.narrative_analysis || []).length > 0 && (
          <Section title="Major Narrative Analysis">
            <div className="space-y-2">
              {(brief.narrative_analysis || []).map((n: string, i: number) => (
                <div key={i} className="flex items-start gap-2">
                  <ChevronRight size={14} className="text-slate-300 mt-1 shrink-0" />
                  <p className="text-white text-sm" dangerouslySetInnerHTML={{ __html: boldify(n) }} />
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Risks */}
        <Section title="Risks" icon={<AlertTriangle size={16} className="text-red-400" />}>
          {!(brief.risks || []).length ? (
            <div className="flex items-center gap-2 text-teal-400"><CheckCircle size={14} /><p className="text-sm">No risks identified this period.</p></div>
          ) : (
            <div className="space-y-3">
              {(brief.risks || []).sort((a: any, b: any) => (a.level_order || 3) - (b.level_order || 3)).map((r: any, i: number) => (
                <div key={i} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={"text-xs font-bold " + RISK_COLOR(r.level)}>{r.level}</span>
                    <span className="text-sm font-semibold text-white" dangerouslySetInnerHTML={{ __html: boldify(r.title) }} />
                    <span className={"ml-auto text-xs " + CONF(r.confidence_label)}>{r.confidence_label}</span>
                  </div>
                  <p className="text-xs text-white mb-1" dangerouslySetInnerHTML={{ __html: boldify(r.detail) }} />
                  <p className="text-xs text-white">Action: {r.action}</p>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Opportunities */}
        <Section title="Opportunities" icon={<Lightbulb size={16} className="text-teal-400" />}>
          {!(brief.opportunities || []).length ? (
            <p className="text-white text-sm">No specific opportunities identified.</p>
          ) : (
            <div className="space-y-3">
              {(brief.opportunities || []).map((o: any, i: number) => (
                <div key={i} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={"text-xs font-bold px-2 py-0.5 rounded-full " + RANK_BADGE(o.rank)}>{o.rank}</span>
                    <span className="text-sm font-semibold text-white" dangerouslySetInnerHTML={{ __html: boldify(o.title) }} />
                  </div>
                  <p className="text-xs text-white mb-1" dangerouslySetInnerHTML={{ __html: boldify(o.detail) }} />
                  <p className="text-xs text-white">Action: {o.action}</p>
                  {o.rationale && <p className="text-xs text-white mt-1">{o.rationale}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Emerging Topics */}
        {(brief.emerging_topics || []).length > 0 && (
          <Section title="Emerging Topics" icon={<TrendingUp size={16} className="text-purple-400" />}>
            <div className="space-y-2">
              {(brief.emerging_topics || []).map((t: any, i: number) => (
                <div key={i} className="flex items-start gap-2">
                  <TrendingUp size={12} className="text-purple-400 mt-1 shrink-0" />
                  <div>
                    <span className="text-sm font-medium text-white">{t.topic}</span>
                    <span className="text-xs text-white ml-2">· {t.category}</span>
                    <p className="text-xs text-white mt-0.5">{t.plain_english}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Diaspora Intelligence */}
        <Section title="Diaspora Intelligence">
          {diasporaNarrative ? (
            <div>
              <p className="text-white text-sm mb-2"
                dangerouslySetInnerHTML={{ __html: boldify(diasporaNarrative.strategic_insight || "") }} />
              <div className="flex gap-4 mt-2">
                <div className="bg-slate-800 rounded-lg p-3 flex-1 text-center">
                  <p className="text-lg font-bold text-white">{diasporaNarrative.share_of_voice}%</p>
                  <p className="text-xs text-white">Share of voice</p>
                </div>
                <div className="bg-slate-800 rounded-lg p-3 flex-1 text-center">
                  <p className={"text-lg font-bold " + (diasporaNarrative.sentiment_label === "positive" ? "text-teal-400" : "text-slate-400")}>
                    {diasporaNarrative.sentiment_label}
                  </p>
                  <p className="text-xs text-white">Sentiment</p>
                </div>
                <div className="bg-slate-800 rounded-lg p-3 flex-1 text-center">
                  <p className="text-lg font-bold text-white">{diasporaNarrative.count}</p>
                  <p className="text-xs text-white">Mentions</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-white text-sm">Diaspora narrative not detected in this period. Consider adding diaspora-specific search queries.</p>
          )}
        </Section>

        {/* Public Sentiment */}
        <Section title="Public Sentiment">
          <p className="text-white text-sm">{brief.sentiment_analysis}</p>
        </Section>

        {/* Coverage Gaps */}
        <Section title="Coverage Gaps" accent="amber" icon={<AlertTriangle size={16} className="text-amber-400" />}>
          {!coverageGaps.length ? (
            <p className="text-white text-sm">No significant coverage gaps detected.</p>
          ) : (
            <div>
              <p className="text-white text-sm mb-2">The following narrative categories have low coverage and may represent monitoring blind spots:</p>
              <div className="flex flex-wrap gap-2">
                {coverageGaps.map((g: string, i: number) => (
                  <span key={i} className="text-xs bg-amber-900/20 border border-amber-700/30 text-amber-300 px-2 py-1 rounded-full">{g}</span>
                ))}
              </div>
              <p className="text-xs text-white mt-2">Add targeted search queries to improve coverage of these areas.</p>
            </div>
          )}
        </Section>

        {/* Confidence Assessment */}
        {brief.source_quality && (
          <Section title="Confidence Assessment" icon={<Shield size={16} className="text-blue-400" />}>
            <p className="text-white text-sm mb-3">{brief.source_quality.summary}</p>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: "Confidence", value: brief.source_quality.overall_confidence_label, color: CONF(brief.source_quality.overall_confidence_label) },
                { label: "Evidence", value: brief.source_quality.total_records?.toLocaleString() + " records" },
                { label: "Sources", value: brief.source_quality.source_count + " active" },
                { label: "Processing", value: brief.source_quality.processing_rate + "%" },
              ].map((item, i) => (
                <div key={i} className="bg-slate-800 rounded-lg p-3 text-center">
                  <p className={"text-sm font-bold " + (item.color || "text-white")}>{item.value}</p>
                  <p className="text-xs text-white mt-0.5">{item.label}</p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Data Quality */}
        {brief.data_quality && (
          <Section title="Data Quality Assessment" icon={<Database size={16} className="text-slate-200" />}>
            <div className="grid grid-cols-3 gap-3 mb-3">
              {[
                { label: "Records ingested", value: brief.data_quality.total_ingested?.toLocaleString() },
                { label: "NLP processed", value: brief.data_quality.nlp_rate + "%" },
                { label: "Topic quality", value: brief.data_quality.topic_quality_rate + "%" },
              ].map((item, i) => (
                <div key={i} className="bg-slate-800 rounded-lg p-3 text-center">
                  <p className="text-sm font-bold text-white">{item.value}</p>
                  <p className="text-xs text-white mt-0.5">{item.label}</p>
                </div>
              ))}
            </div>
            {(brief.data_quality.flags || []).map((f: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs text-white mt-1">
                <AlertTriangle size={12} className="text-amber-400" />{f.message}
              </div>
            ))}
            <p className={"text-xs mt-2 font-medium " + (brief.data_quality.overall_quality === "High" ? "text-teal-400" : brief.data_quality.overall_quality === "Medium" ? "text-amber-400" : "text-red-400")}>
              Overall data quality: {brief.data_quality.overall_quality}
            </p>
          </Section>
        )}

        {/* What To Watch Next */}
        <Section title="What To Watch Next">
          <ul className="space-y-2">
            {(brief.recommended_monitoring || []).map((m: string, i: number) => (
              <li key={i} className="flex items-center gap-2 text-sm text-white">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />{m}
              </li>
            ))}
          </ul>
        </Section>

        {/* Executive Outlook */}
        <Section title="Executive Outlook" accent="blue">
          <p className="text-white text-sm leading-relaxed">{brief.outlook}</p>
        </Section>

        <div className="text-center py-3 text-xs text-white">
          RTIFN National & Diaspora Intelligence Platform (NDIP) · {new Date(brief.generated_at).toLocaleString()} · Aggregated, anonymised data · Not for public distribution
        </div>
      </div>
    </div>
  );
}
// cache bust Sat Jun 13 07:44:28 UTC 2026
