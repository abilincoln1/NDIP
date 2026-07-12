"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { List, AlertTriangle, TrendingUp, Clock, ChevronRight, CheckCircle } from "lucide-react";

const b = (t: string) => t?.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") || "";

const PRIORITY_STYLE: Record<string, string> = {
  Critical: "border-red-600 bg-red-600/10",
  High: "border-orange-500 bg-orange-500/8",
  Medium: "border-amber-500/50 bg-amber-500/5",
  Low: "border-blue-500/30 bg-blue-500/5",
};
const PRIORITY_COLOR: Record<string, string> = {
  Critical: "text-red-400",
  High: "text-orange-400",
  Medium: "text-amber-400",
  Low: "text-blue-400",
};
const ACTION_COLOR: Record<string, string> = {
  Escalate: "bg-red-500/20 text-red-300 border-red-700/30",
  Act: "bg-orange-500/20 text-orange-300 border-orange-700/30",
  Prepare: "bg-amber-500/20 text-amber-300 border-amber-700/30",
  Monitor: "bg-slate-700 text-white border-slate-600",
};

export default function WatchlistPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/watchlist/?days=" + days)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <List size={20} className="text-amber-400" />
            <h1 className="text-3xl font-bold text-white">Leadership Watchlist</h1>
          </div>
          <p className="text-white text-sm">Unified priority intelligence · What requires attention now · NDIP v5.3</p>
          <p className="text-xs text-white mt-1 italic">Aggregated from: National Pulse · Situation Room · Election Centre · Narrative Intelligence · Risk Engine</p>
        </div>
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {[{d:3,l:"3d"},{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"}].map(({d,l}) => (
            <button key={d} onClick={() => setDays(d)}
              className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors " + (days===d?"bg-amber-600 text-white":"text-white hover:text-white")}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner /><p className="text-white text-sm">Generating Leadership Watchlist...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white">Unable to load watchlist.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Summary */}
          <div className={`border rounded-2xl p-6 ${data.critical_count > 0 ? "bg-red-900/20 border-red-700/40" : data.high_count > 0 ? "bg-orange-900/20 border-orange-700/30" : "bg-slate-900 border-slate-800"}`}>
            <div className="flex items-center gap-2 mb-3">
              <List size={16} className={data.critical_count > 0 ? "text-red-400" : data.high_count > 0 ? "text-orange-400" : "text-teal-400"} />
              <span className="text-xs font-bold uppercase tracking-widest text-white">Watchlist Summary</span>
              <span className="ml-auto text-xs text-white">{new Date(data.generated_at).toLocaleString()} · {data.period_days}d window</span>
            </div>
            <p className="text-white text-base leading-relaxed mb-4">{data.summary}</p>
            <div className="flex items-center gap-4">
              {data.critical_count > 0 && <span className="text-xs font-bold text-red-400 bg-red-900/30 border border-red-700/30 px-3 py-1 rounded-full">{data.critical_count} Critical</span>}
              {data.high_count > 0 && <span className="text-xs font-bold text-orange-400 bg-orange-900/30 border border-orange-700/30 px-3 py-1 rounded-full">{data.high_count} High Priority</span>}
              <span className="text-xs text-white">{data.total_items} total items</span>
            </div>
          </div>

          {/* Action Framework Legend */}
          <div className="grid grid-cols-4 gap-3">
            {Object.entries(data.action_framework || {}).map(([action, desc]: [string, any]) => (
              <div key={action} className={`border rounded-xl p-3 text-center ${ACTION_COLOR[action]}`}>
                <p className="text-xs font-bold mb-1">{action}</p>
                <p className="text-xs opacity-80">{desc}</p>
              </div>
            ))}
          </div>

          {/* Watchlist Items */}
          {!(data.items || []).length ? (
            <div className="flex items-center gap-3 p-6 bg-teal-900/10 border border-teal-700/20 rounded-xl">
              <CheckCircle size={18} className="text-teal-400" />
              <div>
                <p className="text-white font-medium">No priority items identified</p>
                <p className="text-sm text-white">Platform is in routine monitoring mode. No critical or high-priority conditions detected.</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {data.items.map((item: any, i: number) => (
                <div key={i} className={`border rounded-2xl p-6 ${PRIORITY_STYLE[item.priority] || "border-slate-700 bg-slate-900"}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={14} className={PRIORITY_COLOR[item.priority]} />
                      <span className={`text-xs font-bold uppercase tracking-wide ${PRIORITY_COLOR[item.priority]}`}>{item.priority}</span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${ACTION_COLOR[item.executive_action]}`}>{item.executive_action}</span>
                      <span className="text-xs text-white bg-slate-800/80 px-2 py-0.5 rounded-full">{item.source_module}</span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-white">
                      <Clock size={11} className="text-white" />
                      <span>{item.recommended_monitoring_period}</span>
                    </div>
                  </div>

                  <p className="text-base font-bold text-white mb-3" dangerouslySetInnerHTML={{ __html: b(item.title) }} />
                  <p className="text-sm text-white leading-relaxed mb-4">{item.why_it_matters}</p>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <p className="text-xs font-bold text-white mb-1">Reason for Inclusion</p>
                      <p className="text-xs text-white">{item.reason_for_inclusion}</p>
                    </div>
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <p className="text-xs font-bold text-white mb-1">Leadership Attention</p>
                      <p className={`text-xs font-semibold ${PRIORITY_COLOR[item.priority]}`}>{item.leadership_attention_level}</p>
                      <p className="text-xs text-white mt-1">{item.action_description}</p>
                    </div>
                  </div>

                  {item.evidence?.count > 0 && (
                    <p className="text-xs text-white mt-3">Based on {item.evidence.count.toLocaleString()} records</p>
                  )}
                </div>
              ))}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
