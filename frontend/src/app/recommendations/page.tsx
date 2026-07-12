"use client";
import { useState, useEffect } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
async function api(path:string, token:string) {
  const r = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  return r.ok ? r.json() : null;
}
const SC: Record<string,string> = { pending:"bg-yellow-100 text-yellow-800", accepted:"bg-green-100 text-green-800", rejected:"bg-red-100 text-red-800", completed:"bg-blue-100 text-blue-800", evaluating:"bg-purple-100 text-purple-800" };
export default function Recommendations() {
  const [recs,setRecs]=useState<any[]>([]);const [total,setTotal]=useState(0);const [loading,setLoading]=useState(true);
  const [sel,setSel]=useState<string|null>(null);const [detail,setDetail]=useState<any>(null);const [tok,setTok]=useState("");
  const [showDec,setShowDec]=useState(false);const [showOut,setShowOut]=useState(false);
  const [decForm,setDecForm]=useState({decision_type:"accept",rationale:"",usefulness_score:4,clarity_score:4});
  const [outForm,setOutForm]=useState({outcome_type:"successful",expected_outcome:"",actual_outcome:"",variance_score:0.7,lessons_learned:""});
  useEffect(()=>{ setTok(localStorage.getItem("token")||""); },[]);
  useEffect(()=>{ if(tok) load(); },[tok]);
  async function load(){ setLoading(true); const d=await api("/api/learning/recommendations?limit=50",tok); if(d){setRecs(d.recommendations||[]);setTotal(d.total||0);} setLoading(false); }
  async function loadDet(id:string){ setSel(id); const d=await api(`/api/learning/recommendations/${id}`,tok); setDetail(d); }
  async function doDecision(){ const r=await fetch(`${API}/api/learning/recommendations/${sel}/decisions`,{method:"POST",headers:{Authorization:`Bearer ${tok}`,"Content-Type":"application/json"},body:JSON.stringify(decForm)}); if(r.ok){setShowDec(false);load();if(sel)loadDet(sel);} }
  async function doOutcome(){ const r=await fetch(`${API}/api/learning/recommendations/${sel}/outcomes`,{method:"POST",headers:{Authorization:`Bearer ${tok}`,"Content-Type":"application/json"},body:JSON.stringify(outForm)}); if(r.ok){setShowOut(false);load();if(sel)loadDet(sel);} }
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div><h1 className="text-xl font-semibold">Recommendation Registry</h1><p className="text-sm text-gray-400">{total} recommendations</p></div>
        <a href="/learning" className="text-sm text-indigo-400">Learning Dashboard</a>
      </div>
      <div className="flex h-[calc(100vh-65px)]">
        <div className="w-80 border-r border-gray-800 overflow-y-auto">
          {loading?<p className="p-4 text-gray-500 text-sm">Loading...</p>:recs.length===0?<p className="p-4 text-gray-500 text-sm">No recommendations yet. They are created automatically when the Copilot generates advice.</p>:recs  .map((r:any)=>(
            <div key={r.id} onClick={()=>loadDet(r.id)} className={`p-4 border-b border-gray-800 cursor-pointer hover:bg-gray-800 ${sel===r.id?"bg-gray-800 border-l-2 border-l-indigo-500":""}`}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="text-sm font-medium text-white line-clamp-2 flex-1">{r.title}</p>
                <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${SC[r.status]||"bg-gray-700 text-gray-300"}`}>{r.status}</span>
              </div>
              <p className="text-xs text-gray-500">{r.category?.replace(/_/g," ")} · {Math.round(r.confidence_at_creation*100)}% · {new Date(r.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {!detail?<p className="text-gray-600 text-sm mt-20 text-center">Select a recommendation to view details</p>:(
            <div className="max-w-2xl">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold">{detail.recommendation.title}</h2>
                  <div className="flex gap-2 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${SC[detail.recommendation.status]||"bg-gray-700 text-gray-300"}`}>{detail.recommendation.status}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">{detail.recommendation.category?.replace(/_/g," ")}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">{Math.round(detail.recommendation.confidence_at_creation*100)}% confidence</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  {!detail.decisions?.length&&<button onClick={()=>setShowDec(true)} className="text-sm bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 rounded">Record Decision</button>}
                  {detail.decisions?.length>0&&detail.decisions[0].decision_type==="accept"&&!detail.outcomes?.length&&<button onClick={()=>{setOutForm(f=>({...f,expected_outcome:detail.recommendation.expected_outcome}));setShowOut(true);}} className="text-sm bg-green-700 hover:bg-green-600 px-3 py-1.5 rounded">Record Outcome</button>}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 mb-4"><p className="text-sm text-gray-300">{detail.recommendation.recommendation_text}</p></div>
              {detail.recommendation.expected_outcome&&<div className="bg-gray-800 rounded p-3 mb-4"><p className="text-xs text-gray-500 mb-1">Expected Outcome</p><p className="text-sm text-gray-300">{detail.recommendation.expected_outcome}</p></div>}
              {detail.decisions?.length>0&&<div className="mb-4"><p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Decision</p>{detail.decisions.map((d:any)=><div key={d.id} className="bg-gray-800 rounded p-3 text-sm mb-1"><span className={`text-xs px-2 py-0.5 rounded mr-2 ${d.decision_type==="accept"?"bg-green-900 text-green-300":"bg-red-900 text-red-300"}`}>{d.decision_type}</span>{d.rationale}</div>)}</div>}
              {detail.checkpoints?.length>0&&<div className="mb-4"><p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Checkpoints</p><div className="flex gap-2 flex-wrap">{detail.checkpoints.map((cp:any)=><span key={cp.id} className={`text-xs px-2 py-1 rounded ${cp.status==="completed"?"bg-green-900 text-green-300":new Date(cp.due_date)<new Date()?"bg-red-900 text-red-300":"bg-gray-700 text-gray-400"}`}>Day {cp.due_days} · {cp.status}</span>)}</div></div>}
              {detail.outcomes?.length>0&&<div className="mb-4"><p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Outcomes</p>{detail.outcomes.map((o:any)=><div key={o.id} className="bg-gray-800 rounded p-3 text-sm mb-2"><span className={`text-xs px-2 py-0.5 rounded mr-2 ${o.outcome_type==="successful"?"bg-green-900 text-green-300":"bg-yellow-900 text-yellow-300"}`}>{o.outcome_type?.replace(/_/g," ")}</span>{o.actual_outcome}{o.lessons_learned&&<p className="text-xs text-gray-500 mt-1">Lesson: {o.lessons_learned}</p>}</div>)}</div>}
              {detail.learning_events?.length>0&&<div className="mb-4"><p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Learning</p>{detail.learning_events.map((e:any)=><div key={e.id} className="bg-gray-800 border border-indigo-800 rounded p-3 text-sm"><p className="text-gray-300 text-xs">{e.learning_statement}</p><span className={`text-xs mt-1 inline-block px-1.5 py-0.5 rounded ${e.validation_status==="validated"?"bg-green-900 text-green-300":"bg-yellow-900 text-yellow-300"}`}>{e.validation_status}</span></div>)}</div>}
            </div>
          )}
        </div>
      </div>
      {showDec&&<div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"><div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96"><h3 className="text-white font-semibold mb-4">Record Decision</h3><select value={decForm.decision_type} onChange={e=>setDecForm(f=>({...f,decision_type:e.target.value}))} className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-3">{["accept","reject","defer","modify","partially_accept","cancel"].map(t=><option key={t} value={t}>{t}</option>)}</select><textarea value={decForm.rationale} onChange={e=>setDecForm(f=>({...f,rationale:e.target.value}))} placeholder="Rationale (optional)" rows={3} className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-3 resize-none"/><div className="flex gap-2"><button onClick={doDecision} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm py-2 rounded">Submit</button><button onClick={()=>setShowDec(false)} className="flex-1 bg-gray-700 text-white text-sm py-2 rounded">Cancel</button></div></div></div>}
      {showOut&&<div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"><div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96"><h3 className="text-white font-semibold mb-4">Record Outcome</h3><select value={outForm.outcome_type} onChange={e=>setOutForm(f=>({...f,outcome_type:e.target.value}))} className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-3">{["successful","partially_successful","unsuccessful","unable_to_evaluate"].map(t=><option key={t} value={t}>{t}</option>)}</select><textarea value={outForm.expected_outcome} onChange={e=>setOutForm(f=>({...f,expected_outcome:e.target.value}))} placeholder="Expected outcome" rows={2} className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-2 resize-none"/><textarea value={outForm.actual_outcome} onChange={e=>setOutForm(f=>({...f,actual_outcome:e.target.value}))} placeholder="What actually happened?" rows={3} className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-2 resize-none"/><textarea value={outForm.lessons_learned} onChange={e=>setOutForm(f=>({...f,lessons_learned:e.target.value}))} placeholder="Lessons learned" rows={2} className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm mb-2 resize-none"/><div className="flex gap-2"><button onClick={doOutcome} className="flex-1 bg-green-700 hover:bg-green-600 text-white text-sm py-2 rounded">Submit</button><button onClick={()=>setShowOut(false)} className="flex-1 bg-gray-700 text-white text-sm py-2 rounded">Cancel</button></div></div></div>}
    </div>
  );
}