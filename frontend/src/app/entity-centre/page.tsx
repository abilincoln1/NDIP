"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Users, TrendingUp, TrendingDown, Minus, AlertTriangle, Star } from "lucide-react";

const MOM = (d: string) => d === "rising" ? <TrendingUp size={12} className="text-teal-400"/> : d === "falling" ? <TrendingDown size={12} className="text-red-400"/> : <Minus size={12} className="text-white/40"/>;
const SENT = (s: string) => s === "positive" ? "text-teal-400" : s === "negative" ? "text-red-400" : "text-white/60";
const TYPE_COLOR: Record<string,string> = { PERSON: "bg-blue-500/20 text-blue-300", ORGANISATION: "bg-purple-500/20 text-purple-300", ORG: "bg-purple-500/20 text-purple-300", LOCATION: "bg-amber-500/20 text-amber-300", GPE: "bg-amber-500/20 text-amber-300", UNKNOWN: "bg-slate-700 text-white/60" };

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-700 rounded-full h-1">
        <div className={`h-1 rounded-full ${color}`} style={{ width: value + "%" }}/>
      </div>
      <span className="text-xs font-bold text-white w-6 text-right">{value}</span>
    </div>
  );
}

export default function EntityCentrePage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"influence"|"rising"|"watchlist">("influence");

  useEffect(() => {
    setLoading(true);
    api.get("/national-pulse/entity-influence?days=" + days)
      .then(r => setData(r.data))
      .catch(() => api.get("/entity-intelligence/?days=" + days).then(r => setData(r.data)))
      .finally(() => setLoading(false));
  }, [days]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Users size={20} className="text-blue-400"/>
            <h1 className="text-3xl font-bold text-white">Entity Intelligence Centre</h1>
          </div>
          <p className="text-white/70 text-sm">Entity influence · Momentum · Rankings · Watchlist · NDIP v5.4</p>
        </div>
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {[{d:3,l:"3d"},{d:7,l:"7d"},{d:14,l:"14d"},{d:30,l:"30d"}].map(({d,l}) => (
            <button key={d} onClick={() => setDays(d)}
              className={"px-3 py-1.5 rounded-md text-xs font-medium transition-colors " + (days===d?"bg-blue-600 text-white":"text-white/60 hover:text-white")}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white/60 text-sm">Computing entity influence...</p></div>
      ) : !data ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center"><p className="text-white/60">Unable to load entity intelligence.</p></div>
      ) : (
        <div className="space-y-6">

          {/* Stats */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Total Entities", value: data.total_entities || data.total_named_entities || "—" },
              { label: "Most Influential", value: data.most_influential?.[0]?.name || "—" },
              { label: "Fastest Rising", value: data.fastest_rising?.[0]?.name || "—" },
              { label: "Watchlist Items", value: data.entity_watchlist?.length || 0 },
            ].map((s,i) => (
              <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <p className="text-sm font-bold text-white truncate">{s.value}</p>
                <p className="text-xs text-white/50 mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* View tabs */}
          <div className="flex gap-2">
            {[{k:"influence",l:"Most Influential"},{k:"rising",l:"Fastest Rising"},{k:"watchlist",l:"Entity Watchlist"}].map(({k,l}) => (
              <button key={k} onClick={() => setView(k as any)}
                className={"px-4 py-2 rounded-lg text-xs font-medium transition-colors " + (view===k?"bg-blue-600 text-white":"bg-slate-800 text-white/60 hover:text-white")}>
                {l}
              </button>
            ))}
          </div>

          {/* Most Influential */}
          {view === "influence" && data.most_influential?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Star size={16} className="text-amber-400"/>
                <h2 className="text-sm font-bold text-white">Most Influential Entities</h2>
                <span className="text-xs text-white/50">Influence Score · Visibility · Sentiment</span>
              </div>
              <div className="space-y-4">
                {data.most_influential.map((e: any, i: number) => (
                  <div key={e.name} className="p-4 bg-slate-800/40 rounded-xl">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">{e.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${TYPE_COLOR[e.entity_type] || TYPE_COLOR.UNKNOWN}`}>{e.entity_type}</span>
                        {MOM(e.momentum_direction)}
                        <span className="text-xs text-white/50">{e.momentum > 0 ? "+" : ""}{e.momentum?.toFixed(0)}%</span>
                      </div>
                      <span className={`text-xs ${SENT(e.sentiment_label)}`}>{e.sentiment_label}</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-white/50 w-20">Influence</span>
                        <ScoreBar value={e.influence_score} color="bg-blue-500"/>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-white/50 w-20">Visibility</span>
                        <ScoreBar value={e.visibility_score} color="bg-purple-500"/>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-white/50 w-20">Leadership</span>
                        <ScoreBar value={e.leadership_index} color="bg-amber-500"/>
                      </div>
                    </div>
                    <p className="text-xs text-white/40 mt-2">{e.mentions} mentions · {e.source_count} sources</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fastest Rising */}
          {view === "rising" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <TrendingUp size={16} className="text-teal-400"/>
                <h2 className="text-sm font-bold text-white">Fastest Rising Entities</h2>
              </div>
              {(data.fastest_rising || []).length > 0 ? (
                <div className="space-y-3">
                  {data.fastest_rising.map((e: any) => (
                    <div key={e.name} className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-xl">
                      <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${TYPE_COLOR[e.entity_type] || TYPE_COLOR.UNKNOWN}`}>{e.entity_type}</span>
                      <span className="text-sm font-semibold text-white flex-1">{e.name}</span>
                      <span className="text-xs text-teal-400 font-bold">+{e.momentum?.toFixed(0)}%</span>
                      <span className="text-xs text-white/50">{e.mentions} mentions</span>
                      <span className={`text-xs ${SENT(e.sentiment_label)}`}>{e.sentiment_label}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-sm">Insufficient historical data for momentum calculation. Check back in 3-7 days.</p>
              )}
            </div>
          )}

          {/* Watchlist */}
          {view === "watchlist" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <AlertTriangle size={16} className="text-amber-400"/>
                <h2 className="text-sm font-bold text-white">Entity Watchlist</h2>
              </div>
              {(data.entity_watchlist || []).length > 0 ? (
                <div className="space-y-3">
                  {data.entity_watchlist.map((w: any, i: number) => (
                    <div key={i} className={`p-4 rounded-xl border ${w.priority === "High" ? "border-orange-500/40 bg-orange-500/5" : "border-amber-500/30 bg-amber-500/5"}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-bold ${w.priority === "High" ? "text-orange-400" : "text-amber-400"}`}>{w.priority}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${TYPE_COLOR[w.type] || TYPE_COLOR.UNKNOWN}`}>{w.type}</span>
                      </div>
                      <p className="text-sm font-semibold text-white">{w.entity}</p>
                      <p className="text-xs text-white/60 mt-1">{w.alert}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-sm">No entities currently on watchlist. Watchlist populates when high-influence entities show unusual momentum or sentiment shifts.</p>
              )}
            </div>
          )}

          {/* Rankings by type */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {[
              { label: "People", data: data.people, color: "text-blue-400" },
              { label: "Organisations", data: data.organisations, color: "text-purple-400" },
              { label: "Locations", data: data.locations, color: "text-amber-400" },
            ].map(({label, data: list, color}) => list?.length > 0 && (
              <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <p className={`text-xs font-bold uppercase tracking-wide mb-3 ${color}`}>{label}</p>
                <div className="space-y-2">
                  {list.slice(0,5).map((e: any) => (
                    <div key={e.name} className="flex items-center justify-between">
                      <span className="text-sm text-white truncate flex-1">{e.name}</span>
                      <span className="text-xs text-white/50 ml-2 shrink-0">{e.mentions}</span>
                      {MOM(e.momentum_direction)}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

        </div>
      )}
    </div>
  );
}
