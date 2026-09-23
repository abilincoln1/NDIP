"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Plus, ChevronLeft, Folder, AlertTriangle, X, Globe, Lock } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  Draft: "bg-slate-700 text-white/70",
  Proposed: "bg-slate-700 text-amber-400",
  "Under Review": "bg-blue-900/40 text-blue-400",
  Approved: "bg-teal-900/40 text-teal-400",
  Active: "bg-teal-900/60 text-teal-300 border border-teal-700/40",
  Paused: "bg-amber-900/40 text-amber-400",
  Completed: "bg-teal-900/30 text-teal-500",
  Cancelled: "bg-red-900/30 text-red-400",
  Archived: "bg-slate-800 text-white/30",
};

function Badge({ label, map }: { label: string; map: Record<string, string> }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${map[label] || "bg-slate-700 text-white/50"}`}>{label}</span>
  );
}

const PROJECT_TYPES = [
  "standard", "independent", "community", "research", "humanitarian",
  "commercial", "government", "academic", "diaspora", "infrastructure", "advocacy", "other"
];

const VISIBILITY_OPTS = [
  { value: "tenant", label: "Tenant (organisation members)" },
  { value: "participating_orgs", label: "Participating organisations" },
  { value: "private", label: "Private (creator only)" },
  { value: "public", label: "Public" },
];

const VALID_TRANSITIONS: Record<string, string[]> = {
  Draft: ["Proposed", "Submitted"],
  Proposed: ["Under Review", "Draft"],
  Submitted: ["Under Review"],
  "Under Review": ["Approved", "Draft"],
  Approved: ["Active"],
  Active: ["Paused", "Completed"],
  Paused: ["Active", "Cancelled"],
};

export default function ProjectsPage() {
  const [view, setView] = useState<"list" | "create" | "detail">("list");
  const [projects, setProjects] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<any>(null);
  const [linkedActivities, setLinkedActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusMsg, setStatusMsg] = useState("");

  const [form, setForm] = useState({
    name: "", description: "", project_type: "community",
    visibility: "tenant", is_independent: false, geo_scope: "unspecified",
  });

  const loadList = () => {
    setLoading(true);
    api.get(`/api/v3/projects/?page=${page}&page_size=20`)
      .then(r => { setProjects(r.data.items || []); setTotal(r.data.total || 0); })
      .catch(() => setError("Failed to load projects"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (view === "list") loadList(); }, [view, page]);

  const openDetail = (p: any) => {
    setSelected(null); setLinkedActivities([]); setStatusMsg(""); setError("");
    api.get(`/api/v3/projects/${p.id}`)
      .then(r => {
        setSelected(r.data);
        setView("detail");
        api.get(`/api/v3/projects/${p.id}/activities`)
          .then(ar => setLinkedActivities(ar.data || [])).catch(() => {});
      })
      .catch(() => setError("Failed to load project"));
  };

  const handleCreate = async () => {
    if (!form.name) { setError("Project name is required"); return; }
    setSaving(true); setError("");
    try {
      await api.post("/api/v3/projects/", {
        name: form.name,
        description: form.description || undefined,
        project_type: form.project_type,
        visibility: form.visibility,
        is_independent: form.is_independent,
        geo_scope: form.geo_scope,
      });
      setView("list"); setPage(1);
      setForm({ name: "", description: "", project_type: "community", visibility: "tenant", is_independent: false, geo_scope: "unspecified" });
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to create project");
    } finally { setSaving(false); }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!selected) return;
    setSaving(true); setError(""); setStatusMsg("");
    try {
      await api.post(`/api/v3/projects/${selected.id}/status`, { status: newStatus });
      const r = await api.get(`/api/v3/projects/${selected.id}`);
      setSelected(r.data);
      setStatusMsg(`Status updated to ${newStatus}`);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Status update failed");
    } finally { setSaving(false); }
  };

  const inputCls = "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-teal-500";
  const labelCls = "block text-xs text-white/60 mb-1";

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          {view !== "list" && (
            <button onClick={() => { setView("list"); setError(""); setStatusMsg(""); }}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white/60 hover:text-white">
              <ChevronLeft size={16} />
            </button>
          )}
          <div>
            <h1 className="text-3xl font-bold text-white">Projects</h1>
            <p className="text-white/60 text-sm">
              {view === "list" ? `${total} projects` : view === "create" ? "New project" : selected?.name}
            </p>
          </div>
        </div>
        {view === "list" && (
          <button onClick={() => { setView("create"); setError(""); }}
            className="flex items-center gap-2 bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded-lg text-sm font-medium">
            <Plus size={16} /> New Project
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
      {statusMsg && (
        <div className="mb-4 bg-teal-900/30 border border-teal-700/40 rounded-xl p-3">
          <p className="text-teal-400 text-sm">{statusMsg}</p>
        </div>
      )}

      {/* LIST */}
      {view === "list" && (
        loading ? (
          <div className="flex justify-center py-24"><Spinner /></div>
        ) : projects.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <p className="text-white/40 text-sm">No projects yet.</p>
            <button onClick={() => setView("create")} className="mt-4 text-teal-400 text-sm hover:text-teal-300">Create the first one →</button>
          </div>
        ) : (
          <div className="space-y-2">
            {projects.map((p: any) => (
              <div key={p.id} onClick={() => openDetail(p)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl p-4 cursor-pointer flex items-center gap-4 transition-colors">
                <Folder size={16} className="text-teal-400/60 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-white font-medium text-sm truncate">{p.name}</span>
                    <Badge label={p.status} map={STATUS_STYLE} />
                    {p.is_independent
                      ? <span className="flex items-center gap-1 text-xs text-amber-400/80"><Globe size={10} />Independent</span>
                      : <span className="flex items-center gap-1 text-xs text-white/40"><Lock size={10} />Tenant</span>}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-white/40">
                    <span>{p.project_type}</span>
                    {p.created_at && <span>{new Date(p.created_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <ChevronLeft size={14} className="text-white/30 rotate-180 shrink-0" />
              </div>
            ))}
            {total > 20 && (
              <div className="flex justify-center gap-3 pt-2">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 text-xs bg-slate-800 text-white/60 rounded-lg disabled:opacity-30">Previous</button>
                <span className="text-xs text-white/40 self-center">Page {page} of {Math.ceil(total / 20)}</span>
                <button disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 text-xs bg-slate-800 text-white/60 rounded-lg disabled:opacity-30">Next</button>
              </div>
            )}
          </div>
        )
      )}

      {/* CREATE */}
      {view === "create" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div>
            <label className={labelCls}>Project Name *</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Project name" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Description</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} placeholder="What is this project?" className={inputCls} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Project Type</label>
              <select value={form.project_type} onChange={e => setForm(f => ({ ...f, project_type: e.target.value }))} className={inputCls}>
                {PROJECT_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Visibility</label>
              <select value={form.visibility} onChange={e => setForm(f => ({ ...f, visibility: e.target.value }))} className={inputCls}>
                {VISIBILITY_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
            <input type="checkbox" id="is_independent" checked={form.is_independent}
              onChange={e => setForm(f => ({ ...f, is_independent: e.target.checked }))}
              className="w-4 h-4 rounded accent-teal-500" />
            <label htmlFor="is_independent" className="text-sm text-white/80 cursor-pointer">
              Independent project — not owned by a single tenant/organisation
            </label>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => { setView("list"); setError(""); }} className="px-4 py-2 text-sm text-white/60 hover:text-white">Cancel</button>
            <button onClick={handleCreate} disabled={saving}
              className="px-5 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
              {saving ? "Saving…" : "Create Project"}
            </button>
          </div>
        </div>
      )}

      {/* DETAIL */}
      {view === "detail" && selected && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge label={selected.status} map={STATUS_STYLE} />
                <Badge label={selected.project_type} map={{}} />
                {selected.is_independent
                  ? <span className="flex items-center gap-1 text-xs text-amber-400"><Globe size={11} />Independent</span>
                  : <span className="flex items-center gap-1 text-xs text-white/40"><Lock size={11} />Tenant-owned</span>}
              </div>
              {/* Status advance buttons */}
              {VALID_TRANSITIONS[selected.status]?.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {VALID_TRANSITIONS[selected.status].map(s => (
                    <button key={s} onClick={() => handleStatusChange(s)} disabled={saving}
                      className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white/70 hover:text-white rounded-lg disabled:opacity-40">
                      → {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <h2 className="text-xl font-bold text-white mb-4">{selected.name}</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              {[
                ["Status", selected.status],
                ["Type", selected.project_type],
                ["Visibility", selected.visibility],
                ["Verification", selected.verification_status || "—"],
                ["Created", selected.created_at ? new Date(selected.created_at).toLocaleDateString() : "—"],
                ["Geography", selected.geography?.state || selected.geo_scope || "—"],
                ["Organisation", selected.originating_org || "—"],
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
          </div>

          {/* Linked Activities */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-sm font-bold text-white mb-3">Linked Activities
              <span className="ml-2 text-white/30 font-normal">({linkedActivities.length})</span>
            </h3>
            {linkedActivities.length === 0 ? (
              <p className="text-white/30 text-sm">No activities linked to this project yet.</p>
            ) : (
              <div className="space-y-2">
                {linkedActivities.map((a: any) => (
                  <div key={a.id} className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-lg text-sm">
                    <span className="text-white/40 text-xs">{a.activity_date}</span>
                    <span className="text-white/60 text-xs">{a.activity_type}</span>
                    <span className="text-white flex-1 truncate">{a.title}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${a.verification_status === "Verified" ? "bg-teal-900/40 text-teal-400" : "bg-slate-700 text-white/50"}`}>
                      {a.verification_status}
                    </span>
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
