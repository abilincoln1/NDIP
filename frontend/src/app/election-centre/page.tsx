"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import {
  Vote, TrendingUp, TrendingDown, AlertTriangle, Lightbulb,
  Clock, CheckCircle, Shield, Target, Eye, BarChart2, ChevronRight, Star, Layers
} from "lucide-react";

const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";
const RISK_STYLE = (l: string) => l === "Critical" ? "border-red-600 bg-red-600/10 text-red-400" : l === "Warning" ? "border-orange-500 bg-orange-500/8 text-orange-400" : l === "Watch" ? "border-amber-500/50 bg-amber-500/5 text-amber-400" : "border-blue-500/30 bg-blue-500/5 text-blue-400";
const CONF = (c: string) => c === "High" ? "text-teal-400" : c === "Medium" ? "text-amber-400" : "text-white";
const RANK_BG = (r: string) => r === "High" ? "bg-teal-500/20 text-teal-300" : r === "Medium" ? "bg-blue-500/20 text-blue-300" : "bg-slate-700 text-white";

function SectionHeader({ icon: Icon, color, label, subtitle }: { icon: any; color: string; label: string; subtitle?: string }) {
  return (
    <div className="flex items-center gap-2 mb-5">
      <Icon size={18} className={color} />
      <h2 className="text-base font-bold text-white">{label}</h2>
      {subtitle && <span className="text-xs text-white ml-1">{subtitle}</span>}
    </div>
  );
}

export default function ElectionCentrePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    api.get("/national-pulse/election-intelligence/full?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Vote size={20} className="text-amber-400" />
            <h1 className="text-3xl font-bold text-white">Election Intelligence Centre</h1>
          </div>
          <p className="text-white text-sm">Nigeria 2027 General Election · Public discourse monitoring · NDIP v5.2</p>
          <p className="text-xs text-white mt-1 italic">Observation only · Not persuasion · Not voter targeting</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
            {[{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"},{d:60,l:"60d"}].map(({d,l}) => (
              <button key={d} onClick={() => setDays(d)}
                className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors " + (days===d?"bg-amber-600 text-white":"text-white hover:text-white")}>
                {l}
              </button>
            ))}
          </div>
          {data && (
            <div className="bg-amber-900/30 border border-amber-700/40 rounded-xl px-5 py-3 text-center">
              <p className="text-3xl font-bold text-amber-400">{data.days_to_election}</p>
              <p className="text-xs text-white mt-1">Days to Election 2027</p>
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner /><p className="text-white text-sm">Generating election intelligence...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white">Unable to load election intelligence.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Executive Election Briefing */}
          <div className="bg-gradient-to-br from-amber-900/30 to-slate-900 border border-amber-700/40 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Star size={16} className="text-amber-400" />
                <span className="text-xs font-bold text-amber-400 uppercase tracking-widest">Executive Election Briefing</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-white bg-amber-900/40 border border-amber-700/30 px-3 py-1 rounded-full">{data.election_phase?.phase}</span>
                <span className="text-xs text-white">{new Date(data.generated_at).toLocaleString()}</span>
              </div>
            </div>
            <p className="text-white text-base leading-relaxed mb-4">{data.executive_briefing?.election_summary}</p>
            {(data.executive_briefing?.key_changes || []).length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-bold text-white uppercase tracking-wider mb-2">Key Changes</p>
                <div className="space-y-1">
                  {data.executive_briefing.key_changes.map((c: string, i: number) => (
                    <div key={i} className="flex items-start gap-2">
                      <ChevronRight size={12} className="text-amber-400 mt-1 shrink-0" />
                      <p className="text-sm text-white">{c}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <p className="text-sm text-white leading-relaxed italic border-t border-amber-700/20 pt-3">{data.executive_briefing?.strategic_summary}</p>
          </div>

          {/* Election Assessment */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={BarChart2} color="text-blue-400" label="A. Election Assessment" subtitle="What happened · Current discourse level · Narrative share"/>
            <div className="grid grid-cols-3 gap-4 mb-5">
              {[
                { label: "Electoral Discourse", value: data.assessment?.current_sov + "%", sub: "Share of voice", color: "text-amber-400" },
                { label: "Election Mentions", value: data.assessment?.current_count?.toLocaleString(), sub: `Last ${days} days`, color: "text-white" },
                { label: "Sentiment", value: data.assessment?.sentiment, sub: "Discourse tone", color: data.assessment?.sentiment === "positive" ? "text-teal-400" : data.assessment?.sentiment === "negative" ? "text-red-400" : "text-white" },
              ].map((item, i) => (
                <div key={i} className="bg-slate-800/60 rounded-xl p-4 text-center">
                  <p className={`text-2xl font-bold mb-1 ${item.color}`}>{item.value}</p>
                  <p className="text-sm font-semibold text-white">{item.label}</p>
                  <p className="text-xs text-white mt-0.5">{item.sub}</p>
                </div>
              ))}
            </div>
            <p className="text-white text-sm leading-relaxed mb-3">{data.assessment?.what_happened}</p>
            <p className="text-white text-sm leading-relaxed mb-3">{data.assessment?.discourse_context}</p>
            <p className="text-white text-sm leading-relaxed">{data.assessment?.momentum_assessment}</p>
          </div>

          {/* Why It Matters */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={Target} color="text-amber-400" label="B. Why It Matters" subtitle="Executive interpretation"/>
            <div className="space-y-4">
              {[
                { label: "Strategic Importance", text: data.why_it_matters?.core_importance },
                { label: "Diaspora Relevance", text: data.why_it_matters?.diaspora_relevance },
                { label: "Current Significance", text: data.why_it_matters?.current_significance },
                { label: "Cross-Narrative Context", text: data.why_it_matters?.cross_narrative_significance },
              ].filter(item => item.text).map((item, i) => (
                <div key={i} className="flex items-start gap-3 p-4 bg-slate-800/40 rounded-xl">
                  <span className="text-xs font-bold text-amber-400 w-32 shrink-0 mt-0.5 uppercase tracking-wide">{item.label}</span>
                  <p className="text-sm text-white leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Strategic Implications */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={Eye} color="text-purple-400" label="C. Strategic Implications" subtitle="Analyst reasoning · Consequences not trends"/>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {Object.entries(data.strategic_implications || {}).map(([key, value]: [string, any]) => (
                <div key={key} className="p-4 bg-slate-800/40 border border-slate-700/50 rounded-xl">
                  <p className="text-xs font-bold text-purple-400 uppercase tracking-wide mb-2">
                    {key.replace(/_/g, " ")}
                  </p>
                  <p className="text-sm text-white leading-relaxed">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Risks and Opportunities */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Risks */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <SectionHeader icon={Shield} color="text-red-400" label="E. Election Risks"/>
              {!(data.risks || []).length ? (
                <div className="flex items-center gap-2 p-4 bg-teal-900/10 border border-teal-700/20 rounded-xl">
                  <CheckCircle size={14} className="text-teal-400" />
                  <p className="text-white text-sm">No critical election risks identified.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {(data.risks || []).map((r: any, i: number) => (
                    <div key={i} className={"border rounded-xl p-4 " + RISK_STYLE(r.level)}>
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle size={13} />
                        <span className="text-xs font-bold uppercase">{r.level}</span>
                        <span className={"ml-auto text-xs " + CONF(r.confidence_label)}>{r.confidence_label}</span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-1">{r.risk}</p>
                      <p className="text-xs text-white leading-relaxed mb-2">{r.detail}</p>
                      <p className="text-xs text-white mb-1"><span className="font-bold">Reasoning:</span> {r.reasoning}</p>
                      <p className="text-xs text-white"><span className="font-bold">Action:</span> {r.action}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Opportunities */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <SectionHeader icon={Lightbulb} color="text-teal-400" label="F. Election Opportunities"/>
              <div className="space-y-3">
                {(data.opportunities || []).map((o: any, i: number) => (
                  <div key={i} className="border border-slate-700 bg-slate-800/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={"text-xs font-bold px-2 py-0.5 rounded-full " + RANK_BG(o.rank)}>{o.rank}</span>
                      <span className={"ml-auto text-xs " + CONF(o.confidence_label)}>{o.confidence_label}</span>
                    </div>
                    <p className="text-sm font-semibold text-white mb-1">{o.opportunity}</p>
                    <p className="text-xs text-white leading-relaxed mb-2">{o.detail}</p>
                    <p className="text-xs text-white mb-1 italic">{o.strategic_context}</p>
                    <p className="text-xs text-white"><span className="font-bold">Action:</span> {o.action}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Election Outlook */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={Clock} color="text-blue-400" label="G. Election Outlook Engine" subtitle="7-day · 14-day · 30-day"/>
            <div className="space-y-4">
              {[
                { key: "7_day", label: "7-Day Outlook" },
                { key: "14_day", label: "14-Day Outlook" },
                { key: "30_day", label: "30-Day Outlook" },
              ].map(({ key, label }) => {
                const o = data.outlook?.[key];
                if (!o) return null;
                return (
                  <div key={key} className="p-5 bg-slate-800/40 rounded-xl">
                    <p className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-3">{label}</p>
                    <p className="text-sm text-white leading-relaxed mb-3">{o.outlook}</p>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                      {[
                        { label: "Drivers", text: o.drivers },
                        { label: "Uncertainties", text: o.uncertainties },
                        { label: "Monitoring", text: o.monitoring },
                      ].map((item, i) => (
                        <div key={i} className="bg-slate-900/50 rounded-lg p-3">
                          <p className="text-xs font-bold text-white mb-1">{item.label}</p>
                          <p className="text-xs text-white leading-relaxed">{item.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
              {data.outlook?.outlook_basis && (
                <p className="text-xs text-white italic">{data.outlook.outlook_basis}</p>
              )}
            </div>
          </div>

          {/* Monitoring Priorities */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={TrendingUp} color="text-amber-400" label="H. Election Monitoring Priorities" subtitle="Leadership Watchlist"/>
            <div className="space-y-3">
              {(data.monitoring_priorities || []).map((p: any, i: number) => (
                <div key={i} className="p-4 bg-amber-900/10 border border-amber-700/20 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-white">{p.priority}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white bg-slate-800 px-2 py-0.5 rounded-full">{p.area}</span>
                      <span className={"text-xs " + CONF(p.confidence_label)}>{p.confidence_label}</span>
                    </div>
                  </div>
                  <p className="text-xs text-white leading-relaxed mb-2">{p.what_to_monitor}</p>
                  <p className="text-xs text-white mb-1 italic">{p.why_it_matters}</p>
                  <p className="text-xs text-white"><span className="font-bold">Period:</span> {p.monitoring_period}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Confidence Framework */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <SectionHeader icon={CheckCircle} color="text-teal-400" label="I. Election Confidence Framework"/>
            <div className="grid grid-cols-3 gap-4 mb-5">
              {[
                { label: "Overall Confidence", value: data.confidence?.overall, color: CONF(data.confidence?.overall) },
                { label: "Data Volume", value: data.confidence?.data_volume, color: "text-white" },
                { label: "Analytical Confidence", value: data.confidence?.analytical_confidence, color: CONF(data.confidence?.analytical_confidence) },
              ].map((item, i) => (
                <div key={i} className="bg-slate-800 rounded-xl p-4 text-center">
                  <p className={`text-lg font-bold mb-1 ${item.color}`}>{item.value}</p>
                  <p className="text-xs text-white">{item.label}</p>
                </div>
              ))}
            </div>
            <div className="space-y-3 mb-4">
              {[
                { label: "Source Coverage", text: data.confidence?.source_coverage },
                { label: "Evidence Strength", text: data.confidence?.evidence_strength },
                { label: "Reasoning", text: data.confidence?.overall_reasoning },
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="text-xs font-bold text-teal-400 w-28 shrink-0 mt-0.5 uppercase tracking-wide">{item.label}</span>
                  <p className="text-sm text-white leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
            <div className="border-t border-slate-700 pt-4">
              <p className="text-xs font-bold text-white mb-2">Known Limitations</p>
              <div className="space-y-1">
                {(data.confidence?.limitations || []).map((l: string, i: number) => (
                  <div key={i} className="flex items-start gap-2">
                    <AlertTriangle size={11} className="text-amber-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-white">{l}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Election Implications Engine */}
          {data.election_implications && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Target size={18} className="text-orange-400"/>
                <h2 className="text-base font-bold text-white">Election Implications Engine</h2>
                <span className="text-xs text-white/50 ml-1">If current trends continue...</span>
              </div>

              <p className="text-white text-sm leading-relaxed mb-5 p-4 bg-orange-900/10 border border-orange-700/20 rounded-xl">
                {data.election_implications.decision_support_summary}
              </p>

              {(data.election_implications.trend_implications || []).length > 0 && (
                <div className="mb-5">
                  <p className="text-xs font-bold text-white uppercase tracking-wider mb-3">Trend Implications</p>
                  <div className="space-y-2">
                    {data.election_implications.trend_implications.map((t: string, i: number) => (
                      <div key={i} className="flex items-start gap-2 p-3 bg-slate-800/40 rounded-lg">
                        <ChevronRight size={12} className="text-orange-400 shrink-0 mt-0.5"/>
                        <p className="text-sm text-white leading-relaxed">{t}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {(data.election_implications.escalating_risks || []).length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">Escalating Risks</p>
                    {data.election_implications.escalating_risks.map((r: any, i: number) => (
                      <div key={i} className="p-3 bg-red-900/10 border border-red-700/20 rounded-lg mb-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-white">{r.risk}</span>
                          <span className="text-xs text-red-400 ml-auto">{r.trajectory}</span>
                        </div>
                        <p className="text-xs text-white/70">{r.detail}</p>
                      </div>
                    ))}
                  </div>
                )}
                {(data.election_implications.emerging_opportunities || []).length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-teal-400 uppercase tracking-wider mb-2">Emerging Opportunities</p>
                    {data.election_implications.emerging_opportunities.map((o: any, i: number) => (
                      <div key={i} className="p-3 bg-teal-900/10 border border-teal-700/20 rounded-lg mb-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-white">{o.opportunity}</span>
                          <span className="text-xs text-teal-400 ml-auto">{o.window}</span>
                        </div>
                        <p className="text-xs text-white/70">{o.detail}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {(data.election_implications.leadership_actions || []).length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-3">Leadership Actions</p>
                  <div className="space-y-2">
                    {data.election_implications.leadership_actions.map((a: any, i: number) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-lg">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${a.priority === "Act" ? "bg-orange-500/20 text-orange-300" : a.priority === "Prepare" ? "bg-amber-500/20 text-amber-300" : "bg-slate-700 text-white"}`}>{a.priority}</span>
                        <div>
                          <p className="text-sm font-semibold text-white">{a.action}</p>
                          <p className="text-xs text-white/60 mt-0.5">{a.timing} · {a.detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Election Narrative Granularity — V5.7 */}
          {data.election_subcategories && data.election_subcategories.subcategory_breakdown?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-2">
                <Layers size={16} className="text-cyan-400"/>
                <h2 className="text-base font-bold text-white">Electoral Discourse Breakdown</h2>
                <span className="text-xs text-white/50 ml-1">What is electoral discourse actually about?</span>
              </div>
              <p className="text-sm text-white/70 mb-4">{data.election_subcategories.what_is_driving_electoral_discourse}</p>

              <div className="space-y-2 mb-4">
                {data.election_subcategories.subcategory_breakdown.map((s: any) => (
                  <div key={s.subcategory} className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white">{s.subcategory}</span>
                        {s.momentum_direction === "rising" && <TrendingUp size={12} className="text-teal-400"/>}
                        {s.momentum_direction === "falling" && <TrendingDown size={12} className="text-red-400"/>}
                        <span className="text-xs text-white/50">{s.momentum > 0 ? "+" : ""}{s.momentum}%</span>
                      </div>
                      <div className="bg-slate-700 rounded-full h-1">
                        <div className="bg-cyan-500 h-1 rounded-full" style={{width: Math.min(s.share_of_election_voice * 2, 100) + "%"}}/>
                      </div>
                    </div>
                    <span className={`text-xs w-16 text-right ${s.sentiment_label === "positive" ? "text-teal-400" : s.sentiment_label === "negative" ? "text-red-400" : "text-white/60"}`}>{s.sentiment_label}</span>
                    <span className="text-sm font-bold text-white tabular-nums w-12 text-right">{s.share_of_election_voice}%</span>
                    <span className="text-xs text-white/40 w-16 text-right">{s.count} posts</span>
                  </div>
                ))}
              </div>

              <div className="flex items-start gap-2 p-3 bg-cyan-900/10 border border-cyan-700/20 rounded-lg">
                <Eye size={12} className="text-cyan-400 shrink-0 mt-0.5"/>
                <p className="text-xs text-white/60 leading-relaxed">{data.election_subcategories.classification_quality_note}</p>
              </div>
            </div>
          )}

          {/* Monitoring Note */}
          <div className="bg-blue-900/10 border border-blue-700/20 rounded-xl p-4">
            <div className="flex items-start gap-2">
              <CheckCircle size={14} className="text-blue-400 mt-0.5 shrink-0" />
              <p className="text-xs text-white leading-relaxed italic">{data.monitoring_note}</p>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
