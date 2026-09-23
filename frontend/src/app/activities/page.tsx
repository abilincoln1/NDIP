"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Plus, ChevronLeft, MapPin, Calendar, Tag, CheckCircle, Clock, AlertTriangle, X } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  Draft: "bg-slate-700 text-white/70",
  Submitted: "bg-amber-900/40 text-amber-400 border border-amber-700/40",
  "Under Review": "bg-blue-900/40 text-blue-400 border border-blue-700/40",
  Verified: "bg-teal-900/40 text-teal-400 border border-teal-700/40",
  Rejected: "bg-red-900/40 text-red-400 border border-red-700/40",
  Archived: "bg-slate-800 text-white/30",
};

const VERIFY_STATUS_STYLE: Record<string, string> = {
  Draft: "bg-slate-700 text-white/70",
  Submitted: "bg-amber-900/40 text-amber-400",
  "Under Review": "bg-blue-900/40 text-blue-400",
  Verified: "bg-teal-900/40 text-teal-400",
  Rejected: "bg-red-900/40 text-red-400",
};

function Badge({ status, map }: { status: string; map: Record<string, string> }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${map[status] || "bg-slate-700 text-white/50"}`}>
      {status}
    </span>
  );
}

export default function ActivitiesPage() {
  const [view, setView] = useState<"list" | "create" | "detail">("list");
  const [activities, setActivities] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actTypes, setActTypes] = useState<any[]>([]);
  const [states, setStates] = useState<any[]>([]);
  const [lgas, setLgas] = useState<any[]>([]);
  const [wards, setWards] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitMsg, setSubmitMsg] = useState("");
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    activity_type: "", title: "", description: "",
    activity_date: new Date().toISOString().slice(0, 10),
    location_text: "", location_state_id: "",
    location_lga_id: "", location_ward_id: "",
    activity_details: "{}",
  });

  const loadList = () => {
    setLoading(true);
    api.get(`/api/v3/activities/?page=${page}&page_size=20`)
      .then(r => { setActivities(r.data.items || []); setTotal(r.data.total || 0); })
      .catch(() => setError("Failed to load activities"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (view === "list") loadList(); }, [view, page]);

  useEffect(() => {
    api.get("/api/v3/activities/types/list").then(r => setActTypes(r.data || [])).catch(() => {});
    api.get("/api/v2/geography/states").then(r => setStates(r.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!form.location_state_id) { setLgas([]); setWards([]); return; }
    api.get(`/api/v2/geography/states/${form.location_state_id}/lgas`)
      .then(r => setLgas(r.data || [])).catch(() => {});
    setForm(f => ({ ...f, location_lga_id: "", location_ward_id: "" }));
    setWards([]);
  }, [form.location_state_id]);

  useEffect(() => {
    if (!form.location_lga_id) { setWards([]); return; }
    api.get(`/api/v2/geography/lgas/${form.location_lga_id}/wards`)
      .then(r => setWards(r.data || [])).catch(() => {});
    setForm(f => ({ ...f, location_ward_id: "" }));
  }, [form.location_lga_id]);

  const openDetail = (act: any) => {
    setSelected(null);
    setSubmitMsg("");
    api.get(`/api/v3/activities/${act.id}`)
      .then(r => { setSelected(r.data); setView("detail"); })
      .catch(() => setError("Failed to load activity"));
  };

  const handleCreate = async () => {
    if (!form.activity_type || !form.title || !form.activity_date) {
      setError("Activity type, title and date are required"); return;
    }
    setSaving(true); setError("");
    try {
      const body: any = {
        activity_type: form.activity_type,
        title: form.title,
        description: form.description || undefined,
        activity_date: form.activity_date,
        location_text: form.location_text || undefined,
        location_state_id: form.location_state_id ? parseInt(form.location_state_id) : undefined,
        location_lga_id: form.location_lga_id ? parseInt(form.location_lga_id) : undefined,
        location_ward_id: form.location_ward_id ? parseInt(form.location_ward_id) : undefined,
      };
      try { body.activity_details = JSON.parse(form.activity_details); } catch { body.activity_details = {}; }
      await api.post("/api/v3/activities/", body);
      setView("list"); setPage(1);
      setForm({ activity_type: "", title: "", description: "", activity_date: new Date().toISOString().slice(0, 10), location_text: "", location_state_id: "", location_lga_id: "", location_ward_id: "", activity_details: "{}" });
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to create activity");
    } finally { setSaving(false); }
  };

  const handleSubmit = async () => {
    if (!selected) return;
    setSaving(true); setSubmitMsg(""); setError("");
    try {
      await api.post(`/api/v3/activities/${selected.id}/verify`, { action: "submit" });
      const r = await api.get(`/api/v3/activities/${selected.id}`);
      setSelected(r.data);
      setSubmitMsg("Submitted for verification");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Submit failed");
    } finally { setSaving(false); }
  };

  const inputCls = "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-teal-500";
  const labelCls = "block text-xs text-white/60 mb-1";

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          {view !== "list" && (
            <button onClick={() => { setView("list"); setError(""); setSubmitMsg(""); }}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white/60 hover:text-white">
              <ChevronLeft size={16} />
            </button>
          )}
          <div>
            <h1 className="text-3xl font-bold text-white">Activities</h1>
            <p className="text-white/60 text-sm">
              {view === "list" ? `${total} records` : view === "create" ? "New activity" : selected?.title}
            </p>
          </div>
        </div>
        {view === "list" && (
          <button onClick={() => { setView("create"); setError(""); }}
            className="flex items-center gap-2 bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded-lg text-sm font-medium">
            <Plus size={16} /> New Activity
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 bg-red-900/30 border border-red-700/40 rounded-xl p-3">
          <AlertTriangle size={14} className="text-red-400 shrink-0" />
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={() => setError("")} className="ml-auto text-red-400/60 hover:text-red-400"><X size={14} /></button>
        </div>
      )}

      {/* LIST VIEW */}
      {view === "list" && (
        loading ? (
          <div className="flex justify-center py-24"><Spinner /></div>
        ) : activities.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <p className="text-white/40 text-sm">No activities yet.</p>
            <button onClick={() => setView("create")} className="mt-4 text-teal-400 text-sm hover:text-teal-300">Create the first one →</button>
          </div>
        ) : (
          <div className="space-y-2">
            {activities.map((a: any) => (
              <div key={a.id} onClick={() => openDetail(a)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl p-4 cursor-pointer flex items-center gap-4 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-white font-medium text-sm truncate">{a.title}</span>
                    <Badge status={a.verification_status} map={VERIFY_STATUS_STYLE} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-white/50">
                    <span className="flex items-center gap-1"><Calendar size={11} />{a.activity_date}</span>
                    <span className="flex items-center gap-1"><Tag size={11} />{a.activity_type}</span>
                    {a.geography?.ward && <span className="flex items-center gap-1"><MapPin size={11} />{a.geography.ward}</span>}
                    {a.location_text && !a.geography?.ward && <span className="flex items-center gap-1"><MapPin size={11} />{a.location_text}</span>}
                  </div>
                </div>
                <ChevronLeft size={14} className="text-white/30 rotate-180 shrink-0" />
              </div>
            ))}
            {total > 20 && (
              <div className="flex justify-center gap-3 pt-2">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 text-xs bg-slate-800 text-white/60 rounded-lg disabled:opacity-30 hover:bg-slate-700">Previous</button>
                <span className="text-xs text-white/40 self-center">Page {page} of {Math.ceil(total / 20)}</span>
                <button disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 text-xs bg-slate-800 text-white/60 rounded-lg disabled:opacity-30 hover:bg-slate-700">Next</button>
              </div>
            )}
          </div>
        )
      )}

      {/* CREATE VIEW */}
      {view === "create" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Activity Type *</label>
              <select value={form.activity_type} onChange={e => setForm(f => ({ ...f, activity_type: e.target.value }))} className={inputCls}>
                <option value="">Select type…</option>
                {actTypes.map((t: any) => <option key={t.id || t.name} value={t.name}>{t.name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Date *</label>
              <input type="date" value={form.activity_date} onChange={e => setForm(f => ({ ...f, activity_date: e.target.value }))} className={inputCls} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Title *</label>
            <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Activity title" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Description</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} placeholder="What happened?" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Location (text)</label>
            <input value={form.location_text} onChange={e => setForm(f => ({ ...f, location_text: e.target.value }))} placeholder="e.g. Birmingham, UK" className={inputCls} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>State (Nigeria)</label>
              <select value={form.location_state_id} onChange={e => setForm(f => ({ ...f, location_state_id: e.target.value }))} className={inputCls}>
                <option value="">Select state…</option>
                {states.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>LGA</label>
              <select value={form.location_lga_id} onChange={e => setForm(f => ({ ...f, location_lga_id: e.target.value }))} disabled={!form.location_state_id} className={inputCls + " disabled:opacity-40"}>
                <option value="">Select LGA…</option>
                {lgas.map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Ward</label>
              <select value={form.location_ward_id} onChange={e => setForm(f => ({ ...f, location_ward_id: e.target.value }))} disabled={!form.location_lga_id} className={inputCls + " disabled:opacity-40"}>
                <option value="">Select ward…</option>
                {wards.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => { setView("list"); setError(""); }} className="px-4 py-2 text-sm text-white/60 hover:text-white">Cancel</button>
            <button onClick={handleCreate} disabled={saving}
              className="px-5 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
              {saving ? "Saving…" : "Create Activity"}
            </button>
          </div>
        </div>
      )}

      {/* DETAIL VIEW */}
      {view === "detail" && selected && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Badge status={selected.verification_status} map={VERIFY_STATUS_STYLE} />
                  <Badge status={selected.activity_type} map={{}} />
                </div>
                <h2 className="text-xl font-bold text-white mt-2">{selected.title}</h2>
              </div>
              {selected.verification_status === "Draft" && (
                <button onClick={handleSubmit} disabled={saving}
                  className="flex items-center gap-2 bg-amber-700/40 hover:bg-amber-700/60 border border-amber-700/40 text-amber-400 px-4 py-2 rounded-lg text-sm disabled:opacity-50">
                  <Clock size={14} /> {saving ? "Submitting…" : "Submit for Verification"}
                </button>
              )}
            </div>
            {submitMsg && <p className="text-teal-400 text-sm mb-4 flex items-center gap-2"><CheckCircle size={14} />{submitMsg}</p>}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              {[
                ["Date", selected.activity_date],
                ["Type", selected.activity_type],
                ["Status", selected.verification_status],
                ["Location", selected.location_text || "—"],
                ["State", selected.geography?.state || "—"],
                ["Ward", selected.geography?.ward || "—"],
                ["Recorded by", selected.recorded_by_name || "—"],
                ["Project", selected.project_name || "—"],
                ["Verified at", selected.verified_at ? new Date(selected.verified_at).toLocaleDateString() : "—"],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="text-white/40 text-xs mb-0.5">{label}</p>
                  <p className="text-white">{value || "—"}</p>
                </div>
              ))}
            </div>
            {selected.description && (
              <div className="mt-4 pt-4 border-t border-slate-800">
                <p className="text-white/40 text-xs mb-1">Description</p>
                <p className="text-white/80 text-sm leading-relaxed">{selected.description}</p>
              </div>
            )}
            {selected.verification_notes && (
              <div className="mt-4 pt-4 border-t border-slate-800">
                <p className="text-white/40 text-xs mb-1">Verification Notes</p>
                <p className="text-white/80 text-sm">{selected.verification_notes}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
