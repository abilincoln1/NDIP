"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Plus, ChevronLeft, Clock, Tag, CheckCircle, AlertTriangle, X } from "lucide-react";

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

const VOL_TYPES = [
  "community", "project_work", "training", "outreach",
  "admin", "mentoring", "fundraising", "advocacy", "other"
];

export default function VolunteersPage() {
  const [view, setView] = useState<"list" | "create" | "detail">("list");
  const [records, setRecords] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    volunteer_type: "",
    description: "",
    volunteer_date: new Date().toISOString().slice(0, 10),
    hours_contributed: "",
    project_id: "",
  });

  const loadList = () => {
    setLoading(true);
    api.get(`/api/v3/volunteer/?page=${page}&page_size=20`)
      .then(r => { setRecords(r.data.items || []); setTotal(r.data.total || 0); })
      .catch(() => setError("Failed to load volunteer records"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (view === "list") loadList(); }, [view, page]);

  const openDetail = (rec: any) => {
    api.get(`/api/v3/volunteer/${rec.id}`)
      .then(r => { setSelected(r.data); setView("detail"); })
      .catch(() => setError("Failed to load record"));
  };

  const handleCreate = async () => {
    if (!form.volunteer_type || !form.volunteer_date) {
      setError("Volunteer type and date are required"); return;
    }
    setSaving(true); setError("");
    try {
      const body: any = {
        volunteer_type: form.volunteer_type,
        description: form.description || undefined,
        volunteer_date: form.volunteer_date,
        hours_contributed: form.hours_contributed ? parseFloat(form.hours_contributed) : undefined,
        project_id: form.project_id || undefined,
        skills_used: [],
      };
      await api.post("/api/v3/volunteer/", body);
      setView("list"); setPage(1);
      setForm({ volunteer_type: "", description: "", volunteer_date: new Date().toISOString().slice(0, 10), hours_contributed: "", project_id: "" });
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to create record");
    } finally { setSaving(false); }
  };

  const inputCls = "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-teal-500";
  const labelCls = "block text-xs text-white/60 mb-1";

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          {view !== "list" && (
            <button onClick={() => { setView("list"); setError(""); }}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white/60 hover:text-white">
              <ChevronLeft size={16} />
            </button>
          )}
          <div>
            <h1 className="text-3xl font-bold text-white">Volunteers</h1>
            <p className="text-white/60 text-sm">
              {view === "list" ? `${total} records` : view === "create" ? "New volunteer record" : selected?.description?.slice(0, 50)}
            </p>
          </div>
        </div>
        {view === "list" && (
          <button onClick={() => { setView("create"); setError(""); }}
            className="flex items-center gap-2 bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded-lg text-sm font-medium">
            <Plus size={16} /> New Record
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

      {/* LIST */}
      {view === "list" && (
        loading ? (
          <div className="flex justify-center py-24"><Spinner /></div>
        ) : records.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <p className="text-white/40 text-sm">No volunteer records yet.</p>
            <button onClick={() => setView("create")} className="mt-4 text-teal-400 text-sm hover:text-teal-300">Create the first one →</button>
          </div>
        ) : (
          <div className="space-y-2">
            {records.map((r: any) => (
              <div key={r.id} onClick={() => openDetail(r)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl p-4 cursor-pointer flex items-center gap-4 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge status={r.volunteer_type} map={{}} />
                    <Badge status={r.verification_status} map={VERIFY_STATUS_STYLE} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-white/50">
                    <span className="flex items-center gap-1"><Clock size={11} />{r.volunteer_date}</span>
                    {r.hours_contributed && <span>{r.hours_contributed}h</span>}
                    {r.description && <span className="truncate max-w-xs">{r.description}</span>}
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

      {/* CREATE */}
      {view === "create" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Volunteer Type *</label>
              <select value={form.volunteer_type} onChange={e => setForm(f => ({ ...f, volunteer_type: e.target.value }))} className={inputCls}>
                <option value="">Select type…</option>
                {VOL_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Date *</label>
              <input type="date" value={form.volunteer_date} onChange={e => setForm(f => ({ ...f, volunteer_date: e.target.value }))} className={inputCls} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Description</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} placeholder="What did you do?" className={inputCls} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Hours Contributed</label>
              <input type="number" step="0.5" min="0" value={form.hours_contributed} onChange={e => setForm(f => ({ ...f, hours_contributed: e.target.value }))} placeholder="e.g. 3.5" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Project ID (optional)</label>
              <input value={form.project_id} onChange={e => setForm(f => ({ ...f, project_id: e.target.value }))} placeholder="Paste project UUID" className={inputCls} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => { setView("list"); setError(""); }} className="px-4 py-2 text-sm text-white/60 hover:text-white">Cancel</button>
            <button onClick={handleCreate} disabled={saving}
              className="px-5 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
              {saving ? "Saving…" : "Create Record"}
            </button>
          </div>
        </div>
      )}

      {/* DETAIL */}
      {view === "detail" && selected && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Badge status={selected.verification_status} map={VERIFY_STATUS_STYLE} />
            <Badge status={selected.volunteer_type} map={{}} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            {[
              ["Date", selected.volunteer_date],
              ["Type", selected.volunteer_type?.replace(/_/g, " ")],
              ["Hours", selected.hours_contributed ?? "—"],
              ["Status", selected.verification_status],
              ["Project", selected.project_name || "—"],
              ["Recorded by", selected.recorded_by_name || "—"],
              ["Activity", selected.activity_title || "—"],
              ["Verified at", selected.verified_at ? new Date(selected.verified_at).toLocaleDateString() : "—"],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-white/40 text-xs mb-0.5">{label}</p>
                <p className="text-white">{String(value ?? "—")}</p>
              </div>
            ))}
          </div>
          {selected.description && (
            <div className="mt-4 pt-4 border-t border-slate-800">
              <p className="text-white/40 text-xs mb-1">Description</p>
              <p className="text-white/80 text-sm leading-relaxed">{selected.description}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
