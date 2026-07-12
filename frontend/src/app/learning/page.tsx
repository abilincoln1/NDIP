"use client";
import { useState, useEffect } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export default function LearningDashboard() {
  const [data,setData]=useState<Record<string,any>|null>(null);const [cals,setCals]=useState<any[]>([]);const [mem,setMem]=useState<any[]>([]);
  const [evs,setEvs]=useState<any[]>([]);const [loading,setLoading]=useState(true);const [tok,setTok]=useState("");const [val,setVal]=useState<string|null>(null);
  useEffect(()=>{ setTok(localStorage.getItem("token")||""); },[]);
  useEffect(()=>{ if(tok) load(); },[tok]);
  async function load(){
    setLoading(true);const h={Authorization:`Bearer ${tok}`};
    const [d,c,m,e]=await Promise.all([
      fetch(`${API}/api/learning/dashboard/summary`,{headers:h}).then(r=>r.ok?r.json():null),
      fetch(`${API}/api/learning/calibration/current`,{headers:h}).then(r=>r.ok?r.json():null),
      fetch(`${API}/api/learning/memory?validation_status=validated&limit=8`,{headers:h}).then(r=>r.ok?r.json():null),
      fetch(`${API}/api/learning/events?status=pending&limit=10`,{headers:h}).then(r=>r.ok?r.json():null),
    ]);
    setData(d);setCals(c?.calibrations||[]);setMem(m?.memory_items||[]);setEvs(e?.learning_events||[]);setLoading(false);
  }
  async function validate(id:string,status:string){ setVal(id); await fetch(`${API}/api/learning/events/${id}/validate`,{method:"PATCH",headers:{Authorization:`Bearer ${tok}`,"Content-Type":"application/json"},body:JSON.stringify({validation_status:status,notes:"Via Dashboard"})}); setVal(null);load(); }
  if(loading)return<div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">Loading...</div>;
  const stats=data?.recommendation_stats||{};
  return(
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div><h1 className="text-xl font-semibold">Strategic Learning Dashboard</h1><p className="text-sm text-gray-400">Continuous learning from operational evidence</p></div>
        <a href="/recommendations" className="text-sm text-indigo-400">Recommendations</a>
      </div>
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[{l:"Success Rate",v:data?.recommendation_success_rate!=null?`${data.recommendation_success_rate}%`:"—",s:`${stats.completed||0} completed`},{l:"Prediction Accuracy",v:data?.prediction_accuracy!=null?`${data.prediction_accuracy}%`:"—",s:"calibration vs outcome"},{l:"Knowledge Items",v:data?.knowledge_items_validated??0,s:"validated lessons"},{l:"Learning Velocity",v:data?.learning_velocity_per_week??0,s:"events this week"}].map(k=>(
            <div key={k.l} className="bg-gray-800 rounded-xl p-4 border border-gray-700"><p className="text-xs text-gray-500 mb-1">{k.l}</p><p className="text-2xl font-bold">{k.v}</p><p className="text-xs text-gray-600 mt-1">{k.s}</p></div>
          ))}
        </div>
        {(data?.pending_learning_validations>0||data?.overdue_checkpoints>0)&&<div className="flex gap-3">
          {data?.pending_learning_validations>0&&<div className="bg-yellow-900/30 border border-yellow-700 rounded px-4 py-2 text-sm text-yellow-300">{data?.pending_learning_validations} learning events awaiting validation</div>}
          {data?.overdue_checkpoints>0&&<div className="bg-red-900/30 border border-red-700 rounded px-4 py-2 text-sm text-red-300">{data?.overdue_checkpoints} checkpoints overdue</div>}
        </div>}
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
            <h3 className="text-sm font-medium mb-4">Confidence Calibration</h3>
            <div className="space-y-3">{cals.map(c=>(
              <div key={c.recommendation_category}>
                <div className="flex justify-between text-xs mb-1"><span className="text-gray-400">{c.recommendation_category.replace(/_/g," ")}</span><span className="font-medium">{(c.current_confidence*100).toFixed(1)}%</span></div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden"><div className="h-full rounded-full" style={{width:`${c.current_confidence*100}%`,backgroundColor:c.sample_size===0?"#4B5563":c.current_confidence>=0.7?"#10B981":"#F59E0B"}}/></div>
                <p className="text-xs text-gray-600 mt-0.5">n={c.sample_size} · {c.update_reason}</p>
              </div>
            ))}</div>
          </div>
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
            <h3 className="text-sm font-medium mb-4">Recommendation Pipeline</h3>
            <div className="space-y-2">{[{l:"Total",v:stats.total||0,c:"text-white"},{l:"Pending",v:stats.pending||0,c:"text-yellow-400"},{l:"Accepted",v:stats.accepted||0,c:"text-green-400"},{l:"Rejected",v:stats.rejected||0,c:"text-red-400"},{l:"Completed",v:stats.completed||0,c:"text-blue-400"}].map(s=>(
              <div key={s.l} className="flex justify-between py-1 border-b border-gray-700"><span className="text-sm text-gray-400">{s.l}</span><span className={`text-sm font-medium ${s.c}`}>{s.v}</span></div>
            ))}</div>
            <a href="/recommendations" className="block mt-4 text-center text-sm bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded">View All Recommendations</a>
          </div>
        </div>
        {evs.length>0&&<div className="bg-gray-800 rounded-xl border border-yellow-700/50 p-5">
          <h3 className="text-sm font-medium mb-4">Pending Validation <span className="ml-2 text-xs bg-yellow-900 text-yellow-300 px-2 py-0.5 rounded">{evs.length}</span></h3>
          <div className="space-y-3">{evs.map(ev=>(
            <div key={ev.id} className="flex items-start justify-between gap-4 py-2 border-b border-gray-700">
              <div className="flex-1"><p className="text-sm text-gray-300">{ev.learning_statement}</p><p className="text-xs text-gray-500 mt-0.5">{ev.significance} significance</p></div>
              <div className="flex gap-2 shrink-0">
                <button onClick={()=>validate(ev.id,"validated")} disabled={val===ev.id} className="text-xs bg-green-800 hover:bg-green-700 text-green-200 px-2 py-1 rounded">{val===ev.id?"...":"Validate"}</button>
                <button onClick={()=>validate(ev.id,"rejected")} disabled={val===ev.id} className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded">Reject</button>
              </div>
            </div>
          ))}</div>
        </div>}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4"><h3 className="text-sm font-medium">Organisational Memory</h3><a href="/memory" className="text-xs text-indigo-400">Browse all</a></div>
          {mem.length===0?<p className="text-sm text-gray-600">No validated knowledge yet. Complete the learning loop to build memory.</p>:<div className="space-y-2">{mem.map(m=>(
            <div key={m.id} className="flex items-start gap-3 py-2 border-b border-gray-700">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0"/>
              <div><p className="text-sm text-gray-300">{m.title}</p><p className="text-xs text-gray-500 mt-0.5">{m.memory_type} · {Math.round(m.confidence_score*100)}% · {m.retrieval_count} retrievals</p></div>
            </div>
          ))}</div>}
        </div>
      </div>
    </div>
  );
}