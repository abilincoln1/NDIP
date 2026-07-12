"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Brain, CheckCircle, AlertCircle, Clock, TrendingUp, RefreshCw } from "lucide-react";

const STATUS_COLOR: Record<string,string> = {
  VALIDATED: "text-teal-400 bg-teal-900/20 border-teal-700/30",
  PARTIALLY_VALIDATED: "text-amber-400 bg-amber-900/20 border-amber-700/30",
  INVALIDATED: "text-red-400 bg-red-900/20 border-red-700/30",
  UNDER_REVIEW: "text-purple-400 bg-purple-900/20 border-purple-700/30",
  OPEN: "text-white/50 bg-slate-800/40 border-slate-700/30",
};

const CATEGORY_COLOR: Record<string,string> = {
  ESCALATE: "text-red-400", ACT: "text-orange-400", ENGAGE: "text-teal-400",
  PREPARE: "text-amber-400", INVESTIGATE: "text-purple-400", MONITOR: "text-white/60",
};

export default function DecisionQualityPage() {
  const [performance, setPerformance] = useState<any>(null);
  const [recs, setRecs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");
  const [running, setRunning] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/national-pulse/decision-support/performance"),
      api.get("/national-pulse/decision-support/recommendations?limit=30" + (filter ? `&status=${filter}` : "")),
    ]).then(([perf, rec]) => {
      setPerformance(perf.data);
      setRecs(rec.data.recommendations || []);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]);

  const runEvaluation = () => {
    setRunning(true);
    api.post("/national-pulse/decision-support/run-evaluation")
      .then(() => load())
      .catch(() => {})
      .finally(() => setRunning(false));
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Brain size={20} className="text-purple-400"/>
            <h1 className="text-3xl font-bold text-white">Decision Quality</h1>
          </div>
          <p className="text-white/70 text-sm">Recommendation effectiveness tracking · Learning Decision Support · NDIP v5.6</p>
        </div>
        <button onClick={runEvaluation} disabled={running}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
          <RefreshCw size={14} className={running ? "animate-spin" : ""}/>
          {running ? "Evaluating..." : "Run Evaluation Cycle"}
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white/60 text-sm">Loading decision quality data...</p></div>
      ) : (
        <div className="space-y-6">

          {/* Performance Summary */}
          {performance && (
            <div className="bg-gradient-to-br from-purple-900/30 to-slate-900 border border-purple-700/30 rounded-2xl p-7">
              <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">Decision Support Performance</p>
              <p className="text-white text-base leading-relaxed mb-5">{performance.narrative_summary}</p>
              <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
                {[
                  { label: "Generated", value: performance.recommendations_generated },
                  { label: "Evaluated", value: performance.recommendations_evaluated },
                  { label: "Validated", value: performance.validated, color: "text-teal-400" },
                  { label: "Partially Validated", value: performance.partially_validated, color: "text-amber-400" },
                  { label: "Invalidated", value: performance.invalidated, color: "text-red-400" },
                  { label: "Avg Accuracy", value: performance.average_accuracy !== null ? performance.average_accuracy + "%" : "N/A", color: "text-purple-400" },
                ].map((s, i) => (
                  <div key={i} className="bg-slate-800/50 rounded-xl p-4 text-center">
                    <p className={`text-2xl font-bold ${s.color || "text-white"}`}>{s.value}</p>
                    <p className="text-xs text-white/50 mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Decision Quality Metrics breakdown */}
          {performance?.metrics && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-sm font-bold text-white mb-4">Decision Quality Metrics by Category</h2>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { label: "Forecast Accuracy", value: performance.metrics.forecast_accuracy },
                  { label: "Action Success Rate", value: performance.metrics.action_success_rate },
                  { label: "Monitoring Success Rate", value: performance.metrics.monitoring_success_rate },
                  { label: "Escalation Accuracy", value: performance.metrics.escalation_accuracy },
                ].map((m, i) => (
                  <div key={i} className="bg-slate-800/40 rounded-xl p-4">
                    <p className="text-xl font-bold text-white">{m.value !== null && m.value !== undefined ? m.value + "%" : "N/A"}</p>
                    <p className="text-xs text-white/50 mt-1">{m.label}</p>
                  </div>
                ))}
              </div>
              {Object.keys(performance.metrics.narrative_prediction_accuracy || {}).length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-bold text-white/60 uppercase tracking-wide mb-2">Narrative Prediction Accuracy</p>
                  {Object.entries(performance.metrics.narrative_prediction_accuracy).map(([n, acc]: any) => (
                    <div key={n} className="flex items-center justify-between py-1.5 border-b border-slate-800 last:border-0">
                      <span className="text-sm text-white">{n}</span>
                      <span className="text-sm font-bold text-purple-400">{acc}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Filter */}
          <div className="flex gap-2">
            {["", "OPEN", "VALIDATED", "PARTIALLY_VALIDATED", "INVALIDATED", "UNDER_REVIEW"].map((s) => (
              <button key={s} onClick={() => setFilter(s)}
                className={"px-3 py-1.5 rounded-lg text-xs font-medium transition-colors " + (filter===s?"bg-purple-600 text-white":"bg-slate-800 text-white/60 hover:text-white")}>
                {s === "" ? "All" : s.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Recommendation list */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-bold text-white mb-4">Tracked Recommendations</h2>
            {recs.length === 0 ? (
              <p className="text-white/50 text-sm">No recommendations tracked yet for this filter.</p>
            ) : (
              <div className="space-y-3">
                {recs.map((r) => (
                  <div key={r.id} className={`border rounded-xl p-4 ${STATUS_COLOR[r.status] || STATUS_COLOR.OPEN}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs font-bold uppercase ${CATEGORY_COLOR[r.category] || "text-white"}`}>{r.category}</span>
                      {r.narrative && <span className="text-xs text-white/50">· {r.narrative}</span>}
                      <span className="text-xs font-bold ml-auto">{r.status.replace("_"," ")}</span>
                      {r.outcome_score !== null && <span className="text-xs font-bold">{r.outcome_score}%</span>}
                    </div>
                    <p className="text-sm text-white mb-2">{r.recommendation_text}</p>
                    {r.outcome_notes && (
                      <p className="text-xs text-white/60 italic border-t border-white/10 pt-2 mt-2">{r.outcome_notes}</p>
                    )}
                    <p className="text-xs text-white/30 mt-2">
                      Created {new Date(r.created_at).toLocaleDateString()} · {r.time_horizon} · {r.confidence} confidence
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
