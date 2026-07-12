"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Brain, TrendingUp, TrendingDown, Minus, Lightbulb, Award, AlertTriangle } from "lucide-react";

const STATUS_COLOR: Record<string,string> = {
  VALIDATED: "text-teal-400 bg-teal-900/20 border-teal-700/30",
  PARTIALLY_VALIDATED: "text-amber-400 bg-amber-900/20 border-amber-700/30",
  INVALIDATED: "text-red-400 bg-red-900/20 border-red-700/30",
  UNDER_REVIEW: "text-purple-400 bg-purple-900/20 border-purple-700/30",
  OPEN: "text-white/50 bg-slate-800/40 border-slate-700/30",
};

const ADJUSTMENT_COLOR: Record<string,string> = {
  Upgrade: "text-teal-400", Maintain: "text-white/70",
  Downgrade: "text-amber-400", "Significant downgrade": "text-red-400",
  "Insufficient data": "text-white/40",
};

const MODULE_LABELS: Record<string,string> = {
  national_pulse: "National Pulse",
  situation_room: "Situation Room",
  leadership_pack: "Leadership Pack",
  election_intelligence: "Election Intelligence",
  gnei: "GNEI",
  entity_intelligence: "Entity Intelligence",
  narrative_intelligence: "Narrative Intelligence",
  decision_support: "Decision Support Engine",
};

export default function IntelligencePerformancePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/national-pulse/intelligence-learning/cycle")
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const metrics = data?.decision_quality_metrics;
  const weights = data?.adaptive_confidence_weights;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Brain size={20} className="text-purple-400"/>
          <h1 className="text-3xl font-bold text-white">Intelligence Performance</h1>
        </div>
        <p className="text-white/70 text-sm">Platform-wide learning · Adaptive confidence · Lessons learned · NDIP v5.8</p>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white/60 text-sm">Computing platform learning cycle...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white/60">Unable to load.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Platform Learning Score */}
          <div className="bg-gradient-to-br from-purple-900/30 to-slate-900 border border-purple-700/30 rounded-2xl p-7">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-2">Platform Learning Score</p>
                <p className="text-white text-sm leading-relaxed max-w-xl">
                  A composite measure of how accurate NDIP's recommendations have proven across
                  all categories, weighted toward metrics with more evaluated volume.
                </p>
              </div>
              <div className="text-center shrink-0 ml-6">
                <p className="text-5xl font-bold text-purple-400">
                  {data.platform_learning_score !== null && data.platform_learning_score !== undefined ? data.platform_learning_score : "N/A"}
                  {data.platform_learning_score !== null && data.platform_learning_score !== undefined && <span className="text-xl text-white/40">/100</span>}
                </p>
              </div>
            </div>
          </div>

          {/* Core metrics grid */}
          {metrics && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: "Generated", value: metrics.recommendations_generated },
                { label: "Evaluated", value: metrics.recommendations_evaluated },
                { label: "Avg Accuracy", value: metrics.average_accuracy !== null ? metrics.average_accuracy + "%" : "N/A" },
                { label: "Forecast Accuracy", value: metrics.forecast_accuracy !== null ? metrics.forecast_accuracy + "%" : "N/A" },
                { label: "Action Success", value: metrics.action_success_rate !== null ? metrics.action_success_rate + "%" : "N/A" },
                { label: "Monitoring Success", value: metrics.monitoring_success_rate !== null ? metrics.monitoring_success_rate + "%" : "N/A" },
                { label: "Outlook Accuracy", value: metrics.outlook_accuracy !== null ? metrics.outlook_accuracy + "%" : "N/A" },
                { label: "Risk Detection", value: metrics.risk_detection_accuracy !== null ? metrics.risk_detection_accuracy + "%" : "N/A" },
              ].map((m, i) => (
                <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xl font-bold text-white">{m.value}</p>
                  <p className="text-xs text-white/50 mt-1">{m.label}</p>
                </div>
              ))}
            </div>
          )}

          {/* Module self-evaluation */}
          {metrics?.module_breakdown && Object.keys(metrics.module_breakdown).length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-sm font-bold text-white mb-4">Module Self-Evaluation</h2>
              <div className="space-y-2">
                {Object.entries(metrics.module_breakdown).map(([mod, d]: any) => (
                  <div key={mod} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <span className="text-sm text-white">{MODULE_LABELS[mod] || mod}</span>
                    <div className="flex items-center gap-4 text-xs text-white/50">
                      <span>{d.generated} generated</span>
                      <span>{d.evaluated} evaluated</span>
                      <span className="font-bold text-purple-400">{d.accuracy !== null ? d.accuracy + "%" : "N/A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Adaptive Confidence Weights */}
          {weights && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-2">
                <Award size={16} className="text-amber-400"/>
                <h2 className="text-sm font-bold text-white">Adaptive Confidence Weighting</h2>
              </div>
              <p className="text-xs text-white/50 mb-4">{weights.methodology_note}</p>
              <p className="text-xs font-bold text-white/60 uppercase tracking-wide mb-2">By Category</p>
              <div className="space-y-2 mb-4">
                {Object.entries(weights.category_weights || {}).map(([cat, w]: any) => (
                  <div key={cat} className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded-lg">
                    <span className="text-sm text-white">{cat}</span>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-white/40">{w.sample_size} samples</span>
                      <span className="text-white/50">{w.historical_accuracy !== null ? w.historical_accuracy + "%" : "—"}</span>
                      <span className={`font-bold ${ADJUSTMENT_COLOR[w.confidence_adjustment] || "text-white"}`}>{w.confidence_adjustment}</span>
                    </div>
                  </div>
                ))}
              </div>
              {Object.keys(weights.narrative_weights || {}).length > 0 && (
                <>
                  <p className="text-xs font-bold text-white/60 uppercase tracking-wide mb-2">By Narrative</p>
                  <div className="space-y-2">
                    {Object.entries(weights.narrative_weights).map(([nar, w]: any) => (
                      <div key={nar} className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded-lg">
                        <span className="text-sm text-white">{nar}</span>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-white/40">{w.sample_size} samples</span>
                          <span className="text-white/50">{w.historical_accuracy !== null ? w.historical_accuracy + "%" : "—"}</span>
                          <span className={`font-bold ${ADJUSTMENT_COLOR[w.confidence_adjustment] || "text-white"}`}>{w.confidence_adjustment}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Lessons Learned */}
          {data.lessons_learned?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb size={16} className="text-amber-400"/>
                <h2 className="text-sm font-bold text-white">Lessons Learned</h2>
              </div>
              <div className="space-y-3">
                {data.lessons_learned.map((l: any, i: number) => (
                  <div key={i} className="p-4 bg-slate-800/40 rounded-xl">
                    <div className="flex items-center gap-2 mb-1">
                      {l.lesson_type === "overconfidence" && <AlertTriangle size={12} className="text-red-400"/>}
                      {l.lesson_type === "reliable_pattern" && <Award size={12} className="text-teal-400"/>}
                      {l.category && <span className="text-xs font-bold text-white/60">{l.category}</span>}
                      <span className="text-xs text-white/30 ml-auto">{l.evidence_count} records</span>
                    </div>
                    <p className="text-sm text-white leading-relaxed">{l.lesson}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Best / Weakest Recommendations */}
          {(data.best_recommendations?.length > 0 || data.weakest_recommendations?.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {data.best_recommendations?.length > 0 && (
                <div className="bg-slate-900 border border-teal-700/20 rounded-xl p-5">
                  <h3 className="text-xs font-bold text-teal-400 uppercase tracking-wide mb-3">Best Performing Recommendations</h3>
                  {data.best_recommendations.map((r: any) => (
                    <div key={r.id} className="py-2 border-b border-slate-800 last:border-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-white/60">{r.category}</span>
                        <span className="text-xs font-bold text-teal-400 ml-auto">{r.outcome_score}%</span>
                      </div>
                      <p className="text-xs text-white/80">{r.recommendation_text?.slice(0,100)}...</p>
                    </div>
                  ))}
                </div>
              )}
              {data.weakest_recommendations?.length > 0 && (
                <div className="bg-slate-900 border border-red-700/20 rounded-xl p-5">
                  <h3 className="text-xs font-bold text-red-400 uppercase tracking-wide mb-3">Weakest Performing Recommendations</h3>
                  {data.weakest_recommendations.map((r: any) => (
                    <div key={r.id} className="py-2 border-b border-slate-800 last:border-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-white/60">{r.category}</span>
                        <span className="text-xs font-bold text-red-400 ml-auto">{r.outcome_score}%</span>
                      </div>
                      <p className="text-xs text-white/80">{r.recommendation_text?.slice(0,100)}...</p>
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
