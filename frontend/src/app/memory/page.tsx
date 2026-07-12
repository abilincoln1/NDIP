"use client";
import { useState, useEffect } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export default function MemoryBrowser() {
  const [items,setItems]=useState<any[]>([]);const [q,setQ]=useState("");const [loading,setLoading]=useState(false);
  const [tok,setTok]=useState("");const [sel,setSel]=useState<string|null>(null);
  useEffect(()=>{ setTok(localStorage.getItem("token")||""); },[]);
  useEffect(()=>{ if(tok) load(); },[tok]);
  async function load(){
    setLoading(true);const h={Authorization:`Bearer ${tok}`};
    const url=q?`${API}/api/learning/memory/search?q=${encodeURIComponent(q)}&limit=20`:`${API}/api/learning/memory?validation_status=validated&limit=20`;
    const r=await fetch(url,{headers:h});if(r.ok){const d=await r.json();setItems(d.results||d.memory_items||[]);}
    setLoading(false);
  }
  return(
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-semibold">Organisational Memory</h1>
        <p className="text-sm text-gray-400">Validated institutional knowledge from operational experience</p>
      </div>
      <div className="p-6">
        <div className="flex gap-3 mb-6">
          <input value={q} onChange={e=>setQ(e.target.value)} onKeyDown={e=>e.key==="Enter"&&load()} placeholder="Search organisational memory..." className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm"/>
          <button onClick={load} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm">Search</button>
          {q&&<button onClick={()=>{setQ("");load();}} className="bg-gray-700 text-white px-3 py-2 rounded-lg text-sm">Clear</button>}
        </div>
        {loading?<p className="text-center text-gray-500 py-8">Searching...</p>:items.length===0?<p className="text-center text-gray-600 py-8">No memory items found</p>:(
          <div className="grid gap-3">{items.map(m=>(
            <div key={m.id} onClick={()=>setSel(sel===m.id?null:m.id)} className="bg-gray-800 border border-gray-700 hover:border-indigo-700 rounded-xl p-4 cursor-pointer transition-colors">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-900 text-indigo-300">{m.memory_type}</span>
                <span className="text-xs text-gray-500">{Math.round((m.confidence_score||0.5)*100)}% confidence</span>
                {m.retrieval_count>0&&<span className="text-xs text-gray-600">{m.retrieval_count} retrievals</span>}
              </div>
              <p className="text-sm font-medium">{m.title}</p>
              {sel===m.id&&<div className="mt-3"><p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{m.content}</p>{m.tags?.length>0&&<div className="flex gap-1 flex-wrap mt-2">{m.tags.map((t:string)=><span key={t} className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">{t}</span>)}</div>}<p className="text-xs text-gray-600 mt-2">{m.source_type} · {new Date(m.created_at).toLocaleDateString()}</p></div>}
            </div>
          ))}</div>
        )}
      </div>
    </div>
  );
}