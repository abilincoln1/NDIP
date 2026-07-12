"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Target, Users, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react";

const STRATEGIC_VALUE_COLOR: Record<string, string> = {
  Critical: "text-red-400 bg-red-900/20 border-red-700/30",
  High: "text-amber-400 bg-amber-900/20 border-amber-700/30",
  Medium: "text-teal-400 bg-teal-900/20 border-teal-700/30",
  Low: "text-white/50 bg-slate-800/40 border-slate-700/30",
};

const PIPELINE_STATUS_ORDER = ["DETECTED", "ASSESSED", "ENGAGED", "IN_PROGRESS", "ADVANCED", "SECURED", "CLOSED", "EXPIRED"];
const PIPELINE_STATUS_LABEL: Record<string, string> = {
  DETECTED: "Detected", ASSESSED: "Assessed", ENGAGED: "Engaged",
  IN_PROGRESS: "In Progress", ADVANCED: "Advanced", SECURED: "Secured",
  CLOSED: "Closed", EXPIRED: "Expired",
};

const PRIORITY_COLOR: Record<string, string> = {
  Critical: "text-red-400", High: "text-amber-400", Medium: "text-teal-400", Low: "text-white/40",
};

const CATEGORY_COLOR: Record<string, string> = {
  POLITICAL: "text-purple-400", PUBLIC_INSTITUTION: "text-blue-400",
  DIASPORA: "text-teal-400", INVESTMENT: "text-amber-400", INTERNATIONAL: "text-pink-400",
};

export default function StrategicOutcomeDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/strategic-outcome/dashboard?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  const pipeline = data?.opportunity_pipeline || {};
  const valueDistribution = data?.strategic_value_distribution || {};
  const outcomeMetrics = data?.strategic_outcome_metrics;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Target size={20} className="text-teal-400" />
          <h1 className="text-3xl font-bold text-white">Strategic Outcome Intelligence</h1>
        </div>
        <p className="text-white/70 text-sm">Opportunities · Stakeholders · Outcome tracking · NDIP v6.0</p>
      </div>

      <div className="flex gap-2 mb-6">
        {[7, 14, 30, 60, 90].map(d => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              days === d ? "bg-teal-600 text-white" : "bg-slate-800 text-white/60 hover:bg-slate-700"
            }`}
          >
            {d}d
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner /><p className="text-white/60 text-sm">Scanning discourse for opportunity and stakeholder signals...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white/60">Unable to load.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Strategic Value Distribution */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {["Critical", "High", "Medium", "Low"].map(v => (
              <div key={v} className={`rounded-xl p-4 border ${STRATEGIC_VALUE_COLOR[v]}`}>
                <p className="text-2xl font-bold">{valueDistribution[v] ?? 0}</p>
                <p className="text-xs mt-1 opacity-80">{v} Value Opportunities</p>
              </div>
            ))}
          </div>

          {/* Opportunity Pipeline */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-bold text-white mb-4">Opportunity Pipeline</h2>
            <div className="flex items-center gap-1 overflow-x-auto pb-2">
              {PIPELINE_STATUS_ORDER.map((status, i) => (
                <div key={status} className="flex items-center shrink-0">
                  <div className="text-center px-3">
                    <p className="text-xl font-bold text-white">{pipeline[status] ?? 0}</p>
                    <p className="text-[10px] text-white/50 mt-0.5 whitespace-nowrap">{PIPELINE_STATUS_LABEL[status]}</p>
                  </div>
                  {i < PIPELINE_STATUS_ORDER.length - 1 && <ArrowRight size={14} className="text-white/20 shrink-0" />}
                </div>
              ))}
            </div>
            {data.generation_summary && (
              <p className="text-xs text-white/40 mt-3">
                {data.generation_summary.created} new opportunities detected this scan ·
                {" "}{data.generation_summary.updated} updated ·
                {" "}{data.generation_summary.below_threshold} signals below tracking threshold
              </p>
            )}
          </div>

          {/* Top Opportunities */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-bold text-white mb-4">Top Opportunities</h2>
            {(!data.top_opportunities || data.top_opportunities.length === 0) ? (
              <p className="text-sm text-white/40">No opportunities detected above the tracking threshold for this period.</p>
            ) : (
              <div className="space-y-3">
                {data.top_opportunities.map((o: any) => (
                  <div key={o.id} className="p-4 bg-slate-800/40 rounded-xl border border-slate-700/30">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <p className="text-sm font-bold text-white">{o.title}</p>
                        <p className="text-xs text-white/50 mt-0.5">{o.category?.replace(/_/g, " ")}</p>
                      </div>
                      <span className={`text-xs font-bold px-2 py-1 rounded-lg border shrink-0 ${STRATEGIC_VALUE_COLOR[o.strategic_value] || ""}`}>
                        {o.strategic_value}
                      </span>
                    </div>
                    <p className="text-sm text-white/80 mb-2">{o.why_it_matters}</p>
                    {o.recommended_engagement && (
                      <p className="text-xs text-teal-400 mb-2"><strong>Action:</strong> {o.recommended_engagement}</p>
                    )}
                    {o.stakeholders?.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap mt-2">
                        <Users size={12} className="text-white/30" />
                        {o.stakeholders.slice(0, 4).map((s: any, i: number) => (
                          <span key={i} className="text-[11px] text-white/60 bg-slate-900 px-2 py-0.5 rounded-md">{s.name}</span>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-white/40">
                      <span>{o.status}</span>
                      <span>{o.confidence} confidence</span>
                      <span>{o.evidence_post_count} mentions</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Stakeholder Rankings */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-bold text-white mb-4">Stakeholder Rankings</h2>
            {(!data.stakeholder_rankings || data.stakeholder_rankings.length === 0) ? (
              <p className="text-sm text-white/40">No stakeholder mentions detected for this period.</p>
            ) : (
              <div className="space-y-2">
                {data.stakeholder_rankings.map((s: any) => (
                  <div key={s.stakeholder_id} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <div>
                      <span className="text-sm text-white">{s.name}</span>
                      <span className={`text-xs ml-2 ${CATEGORY_COLOR[s.category] || "text-white/40"}`}>{s.category?.replace(/_/g, " ")}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-white/50">
                      <span>{s.mention_count} mentions</span>
                      <span className="font-bold text-teal-400">{s.strategic_relevance_score}</span>
                      <span className={`font-bold ${PRIORITY_COLOR[s.monitoring_priority] || "text-white/40"}`}>{s.monitoring_priority}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Engagement Priorities */}
          {data.engagement_priorities?.length > 0 && (
            <div className="bg-amber-900/10 border border-amber-700/30 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={16} className="text-amber-400" />
                <h2 className="text-sm font-bold text-white">Engagement Priorities — Who Leadership Should Engage Next</h2>
              </div>
              <div className="space-y-2">
                {data.engagement_priorities.map((s: any) => (
                  <div key={s.stakeholder_id} className="flex items-center justify-between p-3 bg-slate-900/40 rounded-lg">
                    <span className="text-sm text-white">{s.name}</span>
                    <span className="text-xs text-white/60">{s.recent_activity}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategic Outcome Metrics */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={16} className="text-teal-400" />
              <h2 className="text-sm font-bold text-white">Strategic Outcome Tracker</h2>
            </div>
            {outcomeMetrics?.data_maturity_note ? (
              <p className="text-sm text-white/50">{outcomeMetrics.data_maturity_note}</p>
            ) : (
              <div className="grid grid-cols-3 gap-3 mt-3">
                <div className="text-center">
                  <p className="text-xl font-bold text-white">
                    {outcomeMetrics?.stakeholder_engagement_success !== null && outcomeMetrics?.stakeholder_engagement_success !== undefined
                      ? outcomeMetrics.stakeholder_engagement_success + "%" : "N/A"}
                  </p>
                  <p className="text-xs text-white/50 mt-1">Stakeholder Engagement Success</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold text-white">
                    {outcomeMetrics?.opportunity_conversion_rate !== null && outcomeMetrics?.opportunity_conversion_rate !== undefined
                      ? outcomeMetrics.opportunity_conversion_rate + "%" : "N/A"}
                  </p>
                  <p className="text-xs text-white/50 mt-1">Opportunity Conversion Rate</p>
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold text-white">
                    {outcomeMetrics?.strategic_outcome_success !== null && outcomeMetrics?.strategic_outcome_success !== undefined
                      ? outcomeMetrics.strategic_outcome_success + "%" : "N/A"}
                  </p>
                  <p className="text-xs text-white/50 mt-1">Strategic Outcome Success</p>
                </div>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
