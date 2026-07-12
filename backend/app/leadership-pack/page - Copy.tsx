"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import {
  Shield, TrendingUp, TrendingDown, Minus, AlertTriangle,
  Lightbulb, Clock, CheckCircle, Download, BarChart2, Globe
} from "lucide-react";

const CONF = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-slate-500";
const CONF_BG = (c: string) => c === "High" ? "bg-teal-500/20 text-teal-300 border-teal-700/30" : c === "Medium" ? "bg-amber-500/20 text-amber-300 border-amber-700/30" : "bg-slate-700 text-slate-400 border-slate-600";
const RISK_COLOR = (l: string) => l === "Critical" ? "text-red-400 border-red-600 bg-red-600/10" : l === "Warning" ? "text-orange-400 border-orange-500 bg-orange-500/8" : l === "Watch" ? "text-amber-400 border-amber-500/50 bg-amber-500/5" : "text-blue-400 border-blue-500/30 bg-blue-500/5";
const RANK_COLOR = (r: string) => r === "High" ? "bg-teal-500/20 text-teal-300" : r === "Medium" ? "bg-blue-500/20 text-blue-300" : "bg-slate-700 text-slate-400";
const MOM = (d: string) => d === "rising" ? <TrendingUp size={13} className="text-teal-400"/> : d === "falling" ? <TrendingDown size={13} className="text-red-400"/> : <Minus size={13} className="text-slate-500"/>;
const SENT = (s: string) => s === "positive" ? "text-teal-400" : s === "negative" ? "text-red-400" : "text-slate-400";
const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={"bg-slate-900 border border-slate-800 rounded-xl p-5 " + className}>{children}</div>;
}

function SectionHeader({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle?: string }) {
  return (
    <div className="flex items-center gap-2 mb-5 pb-3 border-b border-slate-800">
      {icon}
      <div>
        <h2 className="text-base font-bold text-white">{title}</h2>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
    </div>
  );
}

function NarrativeCard({ a }: { a: any }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white text-sm">{a.narrative}</span>
          <span className={"text-xs px-2 py-0.5 rounded-full border " + CONF_BG(a.confidence_label)}>{a.confidence_label}</span>
          <span className={"text-xs px-2 py-0.5 rounded-full " + (a.strategic_importance === "High" ? "bg-purple-500/20 text-purple-300" : "bg-slate-700 text-slate-400")}>{a.strategic_importance} priority</span>
        </div>
        <div className="flex items-center gap-2">
          {MOM(a.momentum_direction)}
          <span className={SENT(a.sentiment_label) + " text-xs"}>{a.sentiment_label}</span>
          <span className="text-sm font-bold text-white tabular-nums">{a.share_of_voice}%</span>
        </div>
      </div>
      <div className="space-y-2">
        {[
          { label: "What happened", text: a.what_happened },
          { label: "Why it matters", text: a.why_it_matters },
          { label: "What changed", text: a.what_changed },
          { label: "Leadership action", text: a.leadership_considerations },
        ].map(({ label, text }) => (
          <div key={label} className="flex items-start gap-2">
            <span className="text-xs font-semibold text-slate-500 w-28 shrink-0 mt-0.5">{label}:</span>
            <p className="text-xs text-slate-300 leading-relaxed flex-1" dangerouslySetInnerHTML={{ __html: b(text) }} />
          </div>
        ))}
        <div className="flex items-start gap-2 pt-1 border-t border-slate-700/50">
          <span className="text-xs font-semibold text-blue-400 w-28 shrink-0 mt-0.5">Monitor:</span>
          <p className="text-xs text-slate-400 leading-relaxed flex-1">{a.monitoring_priority}</p>
        </div>
      </div>
    </div>
  );
}

export default function LeadershipPackPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/leadership-pack/?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const download = () => {
    if (!data) return;
    const lines = [
      "RTIFN AGORA OBSERVATORY",
      "LEADERSHIP INTELLIGENCE PACK",
      "Generated: " + new Date(data.generated_at).toLocaleString(),
      "Analysis period: " + data.period_days + " days",
      "=".repeat(60),
      "EXECUTIVE SUMMARY",
      data.executive_summary,
      "",
      "WHAT MATTERS MOST",
      data.what_matters_most,
      "",
      "NATIONAL CONTEXT",
      data.national_context,
      "=".repeat(60),
      "COMPARATIVE INTELLIGENCE",
      ...(data.comparative_intelligence || []).map((c: string) => "• " + c.replace(/\*\*/g, "")),
      "=".repeat(60),
      "NARRATIVE ASSESSMENTS",
      ...(data.narrative_assessments || []).map((a: any) => [
        "",
        a.narrative.toUpperCase() + " [" + a.share_of_voice + "% share of voice | " + a.confidence_label + " confidence]",
        "What happened: " + a.what_happened.replace(/\*\*/g, ""),
        "Why it matters: " + a.why_it_matters,
        "What changed: " + a.what_changed,
        "Leadership action: " + a.leadership_considerations,
        "Monitor: " + a.monitoring_priority,
      ].join("\n")),
      "=".repeat(60),
      "RISKS",
      ...(data.risks || []).map((r: any) => "[" + r.level + "] " + r.title + ": " + r.detail + "\nAction: " + r.action),
      "=".repeat(60),
      "OPPORTUNITIES",
      ...(data.opportunities || []).map((o: any) => "[" + o.rank + "] " + o.title + ": " + o.detail + "\nAction: " + o.action),
      "=".repeat(60),
      "OUTLOOK",
      "7 days: " + (data.outlook?.["7_day"] || "").replace(/\*\*/g, ""),
      "14 days: " + (data.outlook?.["14_day"] || "").replace(/\*\*/g, ""),
      "30 days: " + (data.outlook?.["30_day"] || "").replace(/\*\*/g, ""),
      "=".repeat(60),
      "CONFIDENCE STATEMENT",
      (data.confidence_statement?.summary || "").replace(/\*\*/g, ""),
      "Limitations: " + (data.confidence_statement?.limitations || []).join(". "),
      "=".repeat(60),
      "RTIFN Agora Observatory — Aggregated, anonymised data only — Not for public distribution",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "RTIFN-Leadership-Pack-" + new Date().toISOString().slice(0, 10) + ".txt";
    a.click();
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Leadership Intelligence Pack</h1>
          <p className="text-slate-400 text-sm">Board-ready intelligence briefing · RTIFN Agora Observatory</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2">
            {[{d:3,l:"3d"},{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"}].map(({d,l}) => (
              <button key={d} onClick={() => setDays(d)}
                className={"px-3 py-2 rounded-lg text-xs font-medium transition-colors " + (days===d?"bg-blue-600 text-white":"bg-slate-800 text-slate-400 hover:text-white")}>
                {l}
              </button>
            ))}
          </div>
          <button onClick={download} className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg px-4 py-2 text-sm transition-colors font-medium">
            <Download size={14} />Download Pack
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner /><p className="text-slate-500 text-sm">Preparing leadership intelligence pack...</p></div>
      ) : !data ? (
        <Card className="text-center py-16"><p className="text-slate-400">Unable to load. Please try again.</p></Card>
      ) : (
        <div className="space-y-6">

          {/* SECTION 1: Executive Summary */}
          <div className="bg-gradient-to-r from-blue-900/40 to-slate-900 border border-blue-700/40 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"/>
              <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">Section 1 — Executive Summary</span>
              <span className="ml-auto text-xs text-slate-500">{new Date(data.generated_at).toLocaleString()} · {data.period_days}-day window</span>
            </div>
            <p className="text-white text-base leading-relaxed mb-4">{data.executive_summary}</p>
            {data.national_context && (
              <div className="bg-blue-900/20 border border-blue-700/20 rounded-lg p-3 mt-3">
                <p className="text-xs text-slate-400 font-semibold mb-1 uppercase tracking-wider">National Context</p>
                <p className="text-slate-200 text-sm leading-relaxed">{data.national_context}</p>
              </div>
            )}
            {(data.comparative_intelligence || []).length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Comparative Intelligence</p>
                {data.comparative_intelligence.map((c: string, i: number) => (
                  <p key={i} className="text-sm text-slate-300" dangerouslySetInnerHTML={{ __html: b(c) }} />
                ))}
              </div>
            )}
          </div>

          {/* SECTION 2: Narrative Assessments */}
          <Card>
            <SectionHeader
              icon={<BarChart2 size={18} className="text-purple-400"/>}
              title="Section 2 — Narrative Assessment"
              subtitle="Analyst-grade assessment of each monitored narrative"
            />
            {(data.narrative_assessments || []).map((a: any) => (
              <NarrativeCard key={a.narrative} a={a} />
            ))}
          </Card>

          {/* SECTION 3: Three intelligence streams */}
          <div className="space-y-4">
            {/* Diaspora Intelligence */}
            {data.diaspora_intelligence?.assessment && (
              <Card>
                <SectionHeader
                  icon={<Globe size={18} className="text-blue-400"/>}
                  title="Section 3A — Global Nigerian Engagement Intelligence"
                  subtitle="Overseas Nigerian community · Advocacy · Migration · Remittances · Civic participation"
                />
                <NarrativeCard a={data.diaspora_intelligence.assessment} />
              </Card>
            )}

            {/* National Intelligence */}
            {(data.national_intelligence?.assessments || []).length > 0 && (
              <Card>
                <SectionHeader
                  icon={<Shield size={18} className="text-amber-400"/>}
                  title="Section 3B — National Nigeria Intelligence"
                  subtitle="Economy · Security · Governance · Infrastructure · Energy · Education · Health"
                />
                {data.national_intelligence.assessments.map((a: any) => (
                  <NarrativeCard key={a.narrative} a={a} />
                ))}
              </Card>
            )}

            {/* Emerging Intelligence */}
            <Card>
              <SectionHeader
                icon={<TrendingUp size={18} className="text-teal-400"/>}
                title="Section 3C — Emerging Issues Intelligence"
                subtitle="Rapidly growing narratives · Early warning indicators · Monitoring priorities"
              />
              <p className="text-slate-300 text-sm mb-3">{data.emerging_intelligence?.description}</p>
              {(data.emerging_intelligence?.narratives || []).length > 0 ? (
                <div className="space-y-3">
                  {data.emerging_intelligence.narratives.map((n: any) => (
                    <div key={n.narrative} className="flex items-center gap-3 p-3 bg-teal-900/10 border border-teal-700/20 rounded-lg">
                      <TrendingUp size={14} className="text-teal-400 shrink-0"/>
                      <div className="flex-1">
                        <span className="text-sm font-semibold text-white">{n.narrative}</span>
                        <span className="text-xs text-slate-500 ml-2">{n.share_of_voice}% share of voice · {n.count} mentions</span>
                      </div>
                      <span className="text-xs text-teal-400 font-medium">Rapidly emerging</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-slate-500">
                  <CheckCircle size={14} className="text-teal-400"/>
                  <span className="text-sm">No unusual emerging issues detected.</span>
                </div>
              )}
            </Card>
          </div>

          {/* SECTION 4: Risks & Opportunities */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card>
              <SectionHeader icon={<AlertTriangle size={18} className="text-red-400"/>} title="Section 4A — Risks"/>
              {!(data.risks||[]).filter((r:any)=>r.level!=="Information").length ? (
                <div className="flex items-center gap-2 text-teal-400"><CheckCircle size={14}/><span className="text-sm">No critical risks identified.</span></div>
              ) : (
                <div className="space-y-3">
                  {(data.risks||[]).sort((a:any,b:any)=>(a.level_order||3)-(b.level_order||3)).map((r:any,i:number) => (
                    <div key={i} className={"border rounded-xl p-4 " + RISK_COLOR(r.level)}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-bold uppercase">{r.level}</span>
                        <span className={"ml-auto text-xs " + CONF(r.confidence_label)}>{r.confidence_label}</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1" dangerouslySetInnerHTML={{__html:b(r.title)}}/>
                      <p className="text-xs text-slate-300 mb-2" dangerouslySetInnerHTML={{__html:b(r.detail)}}/>
                      <p className="text-xs text-slate-400">Action: {r.action}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <SectionHeader icon={<Lightbulb size={18} className="text-teal-400"/>} title="Section 4B — Opportunities"/>
              {!(data.opportunities||[]).length ? (
                <p className="text-slate-500 text-sm">No specific opportunities identified.</p>
              ) : (
                <div className="space-y-3">
                  {(data.opportunities||[]).map((o:any,i:number) => (
                    <div key={i} className="border border-slate-700 bg-slate-800/30 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={"text-xs font-bold px-2 py-0.5 rounded-full " + RANK_COLOR(o.rank)}>{o.rank}</span>
                        <span className={"ml-auto text-xs " + CONF(o.confidence_label)}>{o.confidence_label}</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1" dangerouslySetInnerHTML={{__html:b(o.title)}}/>
                      <p className="text-xs text-slate-300 mb-2" dangerouslySetInnerHTML={{__html:b(o.detail)}}/>
                      <p className="text-xs text-slate-400">Action: {o.action}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* SECTION 5: Outlook */}
          {data.outlook && (
            <Card>
              <SectionHeader icon={<Clock size={18} className="text-slate-400"/>} title="Section 5 — Executive Outlook"/>
              <div className="space-y-4">
                {[
                  {key:"7_day", label:"7-Day Outlook"},
                  {key:"14_day", label:"14-Day Outlook"},
                  {key:"30_day", label:"30-Day Outlook"},
                ].map(({key,label}) => (
                  <div key={key} className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg">
                    <span className="text-xs font-bold text-slate-400 w-24 shrink-0 mt-0.5">{label}</span>
                    <p className="text-sm text-slate-300 leading-relaxed flex-1"
                      dangerouslySetInnerHTML={{__html:b(data.outlook[key]||"")}}/>
                  </div>
                ))}
              </div>
              {(data.outlook.monitoring_priorities||[]).length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <p className="text-xs font-semibold text-slate-400 mb-2">Monitoring priorities:</p>
                  <div className="flex flex-wrap gap-2">
                    {data.outlook.monitoring_priorities.map((p:string,i:number) => (
                      <span key={i} className="text-xs bg-blue-900/30 border border-blue-700/30 text-blue-300 px-2 py-1 rounded-full">{p}</span>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* SECTION 6: Confidence Statement */}
          {data.confidence_statement && (
            <Card>
              <SectionHeader icon={<CheckCircle size={18} className="text-teal-400"/>} title="Section 6 — Confidence Statement"/>
              <p className="text-slate-300 text-sm mb-4" dangerouslySetInnerHTML={{__html:b(data.confidence_statement.summary)}}/>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
                {[
                  {label:"Overall Rating", value:data.confidence_statement.overall_rating, colored:true},
                  {label:"Data Quality", value:data.confidence_statement.data_quality, colored:true},
                  {label:"Source Coverage", value:data.confidence_statement.source_coverage},
                  {label:"Evidence", value:data.confidence_statement.evidence_volume},
                  {label:"Processing", value:data.confidence_statement.processing_rate},
                ].map((item,i) => (
                  <div key={i} className="bg-slate-800 rounded-lg p-3 text-center">
                    <p className={"text-sm font-bold " + (item.colored ? CONF(item.value) : "text-white")}>{item.value}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{item.label}</p>
                  </div>
                ))}
              </div>
              {(data.confidence_statement.limitations||[]).map((l:string,i:number) => (
                <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
                  <AlertTriangle size={12} className="text-amber-400 mt-0.5 shrink-0"/>{l}
                </div>
              ))}
            </Card>
          )}

          <div className="text-center py-4 border-t border-slate-800">
            <p className="text-xs text-slate-600">
              RTIFN Agora Observatory · Leadership Intelligence Pack · {new Date(data.generated_at).toLocaleString()} · Aggregated, anonymised data · Not for public distribution
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
