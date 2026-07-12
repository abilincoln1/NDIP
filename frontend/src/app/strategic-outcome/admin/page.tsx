"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Spinner } from "@/components/ui";
import { Database, Plus, Trash2, Users, Target, Link2, X } from "lucide-react";

type Tab = "stakeholders" | "opportunities" | "relationships";

const STAKEHOLDER_CATEGORIES = ["POLITICAL", "PUBLIC_INSTITUTION", "DIASPORA", "INVESTMENT", "INTERNATIONAL"];
const OPPORTUNITY_CATEGORIES = [
  "INFRASTRUCTURE", "ENERGY", "WASTE_TO_ENERGY", "CLIMATE_FINANCE", "CARBON_MARKETS",
  "DIASPORA_INVESTMENT", "PPP", "FEDERAL_PROGRAMMES", "STATE_PROGRAMMES", "DEVELOPMENT_FINANCE",
  "INTERNATIONAL_DONOR", "INNOVATION_ENTREPRENEURSHIP", "TRADE_INVESTMENT", "INDUSTRIAL_DEVELOPMENT",
  "WASTE_MANAGEMENT", "RENEWABLE_ENERGY", "RURAL_ELECTRIFICATION", "ENERGY_ACCESS", "GREEN_INVESTMENT",
];
const RELATIONSHIP_TYPES = ["REPORTS_TO", "OWNS_PROGRAMME", "FUNDS", "REGULATES", "PARTNERS_WITH"];

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-lg w-full max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-bold text-white">{title}</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white"><X size={18}/></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <label className="text-xs text-white/60 mb-1 block">{label}</label>
      {children}
    </div>
  );
}

const inputClass = "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white";

export default function RegistryAdminPage() {
  const [tab, setTab] = useState<Tab>("stakeholders");
  const [stakeholders, setStakeholders] = useState<any[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [relationships, setRelationships] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<null | "new-stakeholder" | "new-opportunity" | "new-relationship">(null);
  const [form, setForm] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/strategic-outcome/registry/stakeholders"),
      api.get("/strategic-outcome/registry/opportunities"),
      api.get("/strategic-outcome/v61/relationships"),
    ])
      .then(([s, o, r]) => {
        setStakeholders(s.data.stakeholders || []);
        setOpportunities(o.data.opportunity_types || []);
        setRelationships(r.data.relationships || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const submitStakeholder = async () => {
    setSaving(true); setError("");
    try {
      await api.post("/strategic-outcome/registry/stakeholders", {
        name: form.name, short_name: form.short_name, category: form.category,
        sector: form.sector, role_description: form.role_description,
        aliases: (form.aliases_text || "").split(",").map((a: string) => a.trim()).filter(Boolean),
      });
      setModal(null); setForm({}); load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to add stakeholder.");
    } finally { setSaving(false); }
  };

  const submitOpportunity = async () => {
    setSaving(true); setError("");
    try {
      await api.post("/strategic-outcome/registry/opportunities", {
        name: form.name, category: form.category, description: form.description,
        aliases: (form.aliases_text || "").split(",").map((a: string) => a.trim()).filter(Boolean),
      });
      setModal(null); setForm({}); load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to add opportunity type.");
    } finally { setSaving(false); }
  };

  const submitRelationship = async () => {
    setSaving(true); setError("");
    try {
      await api.post("/strategic-outcome/v61/relationships", {
        from_stakeholder_id: Number(form.from_id), to_stakeholder_id: Number(form.to_id),
        relationship_type: form.relationship_type, description: form.description,
        relevant_category: form.relevant_category || null,
      });
      setModal(null); setForm({}); load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to add relationship.");
    } finally { setSaving(false); }
  };

  const deactivateStakeholder = async (id: number) => {
    if (!confirm("Deactivate this stakeholder? It will stop appearing in rankings but its history is preserved.")) return;
    await api.delete(`/strategic-outcome/registry/stakeholders/${id}`);
    load();
  };
  const deactivateOpportunity = async (id: number) => {
    if (!confirm("Deactivate this opportunity type?")) return;
    await api.delete(`/strategic-outcome/registry/opportunities/${id}`);
    load();
  };
  const deactivateRelationship = async (id: number) => {
    if (!confirm("Deactivate this relationship?")) return;
    await api.delete(`/strategic-outcome/v61/relationships/${id}`);
    load();
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Database size={20} className="text-teal-400"/>
          <h1 className="text-3xl font-bold text-white">Registry Management</h1>
        </div>
        <p className="text-white/70 text-sm">Stakeholders · Opportunity Types · Relationships — expand coverage without code changes · NDIP v6.1</p>
      </div>

      <div className="flex gap-2 mb-6">
        {[
          { id: "stakeholders", label: "Stakeholders", icon: Users },
          { id: "opportunities", label: "Opportunity Types", icon: Target },
          { id: "relationships", label: "Relationships", icon: Link2 },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id as Tab)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              tab === id ? "bg-teal-600 text-white" : "bg-slate-800 text-white/60 hover:bg-slate-700"
            }`}
          >
            <Icon size={13}/> {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex flex-col items-center py-24 gap-3"><Spinner/><p className="text-white/60 text-sm">Loading registries...</p></div>
      ) : (
        <div className="space-y-4">

          {tab === "stakeholders" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-white">{stakeholders.length} Stakeholders</h2>
                <button onClick={() => { setForm({}); setError(""); setModal("new-stakeholder"); }}
                  className="flex items-center gap-1.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg">
                  <Plus size={13}/> Add Stakeholder
                </button>
              </div>
              <div className="space-y-2">
                {stakeholders.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <div>
                      <span className="text-sm text-white font-medium">{s.name}</span>
                      <span className="text-xs text-white/40 ml-2">{s.category} · {s.sector}</span>
                    </div>
                    <button onClick={() => deactivateStakeholder(s.id)} className="text-white/30 hover:text-red-400">
                      <Trash2 size={14}/>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "opportunities" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-white">{opportunities.length} Opportunity Types</h2>
                <button onClick={() => { setForm({}); setError(""); setModal("new-opportunity"); }}
                  className="flex items-center gap-1.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg">
                  <Plus size={13}/> Add Opportunity Type
                </button>
              </div>
              <div className="space-y-2">
                {opportunities.map((o) => (
                  <div key={o.id} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <div>
                      <span className="text-sm text-white font-medium">{o.name}</span>
                      <span className="text-xs text-white/40 ml-2">{o.category?.replace(/_/g, " ")}</span>
                    </div>
                    <button onClick={() => deactivateOpportunity(o.id)} className="text-white/30 hover:text-red-400">
                      <Trash2 size={14}/>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "relationships" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-white">{relationships.length} Relationships</h2>
                <button onClick={() => { setForm({}); setError(""); setModal("new-relationship"); }}
                  className="flex items-center gap-1.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg">
                  <Plus size={13}/> Add Relationship
                </button>
              </div>
              <div className="space-y-2">
                {relationships.map((r) => (
                  <div key={r.id} className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg">
                    <div className="text-sm text-white">
                      <span className="font-medium">{r.from}</span>
                      <span className="text-white/40 mx-2">{r.type.replace(/_/g, " ")}</span>
                      <span className="font-medium">{r.to}</span>
                    </div>
                    <button onClick={() => deactivateRelationship(r.id)} className="text-white/30 hover:text-red-400">
                      <Trash2 size={14}/>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}

      {modal === "new-stakeholder" && (
        <Modal title="Add Stakeholder" onClose={() => setModal(null)}>
          <Field label="Name *"><input className={inputClass} value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })}/></Field>
          <Field label="Short Name"><input className={inputClass} value={form.short_name || ""} onChange={(e) => setForm({ ...form, short_name: e.target.value })}/></Field>
          <Field label="Category *">
            <select className={inputClass} value={form.category || ""} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="">Select...</option>
              {STAKEHOLDER_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Sector"><input className={inputClass} value={form.sector || ""} onChange={(e) => setForm({ ...form, sector: e.target.value })}/></Field>
          <Field label="Role Description"><textarea className={inputClass} rows={2} value={form.role_description || ""} onChange={(e) => setForm({ ...form, role_description: e.target.value })}/></Field>
          <Field label="Aliases (comma-separated, used for discourse matching)"><input className={inputClass} placeholder="e.g. rea, rural electrification agency" value={form.aliases_text || ""} onChange={(e) => setForm({ ...form, aliases_text: e.target.value })}/></Field>
          {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
          <button disabled={saving || !form.name || !form.category} onClick={submitStakeholder}
            className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white text-sm font-medium py-2 rounded-lg">
            {saving ? "Saving..." : "Add Stakeholder"}
          </button>
        </Modal>
      )}

      {modal === "new-opportunity" && (
        <Modal title="Add Opportunity Type" onClose={() => setModal(null)}>
          <Field label="Name *"><input className={inputClass} value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })}/></Field>
          <Field label="Category *">
            <select className={inputClass} value={form.category || ""} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="">Select...</option>
              {OPPORTUNITY_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </Field>
          <Field label="Description"><textarea className={inputClass} rows={2} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })}/></Field>
          <Field label="Aliases (comma-separated)"><input className={inputClass} placeholder="e.g. mini-grid, mini grid programme" value={form.aliases_text || ""} onChange={(e) => setForm({ ...form, aliases_text: e.target.value })}/></Field>
          {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
          <button disabled={saving || !form.name || !form.category} onClick={submitOpportunity}
            className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white text-sm font-medium py-2 rounded-lg">
            {saving ? "Saving..." : "Add Opportunity Type"}
          </button>
        </Modal>
      )}

      {modal === "new-relationship" && (
        <Modal title="Add Relationship" onClose={() => setModal(null)}>
          <Field label="From Stakeholder *">
            <select className={inputClass} value={form.from_id || ""} onChange={(e) => setForm({ ...form, from_id: e.target.value })}>
              <option value="">Select...</option>
              {stakeholders.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Relationship Type *">
            <select className={inputClass} value={form.relationship_type || ""} onChange={(e) => setForm({ ...form, relationship_type: e.target.value })}>
              <option value="">Select...</option>
              {RELATIONSHIP_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </Field>
          <Field label="To Stakeholder *">
            <select className={inputClass} value={form.to_id || ""} onChange={(e) => setForm({ ...form, to_id: e.target.value })}>
              <option value="">Select...</option>
              {stakeholders.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Description"><textarea className={inputClass} rows={2} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })}/></Field>
          <Field label="Relevant Opportunity Category (optional)">
            <select className={inputClass} value={form.relevant_category || ""} onChange={(e) => setForm({ ...form, relevant_category: e.target.value })}>
              <option value="">None</option>
              {OPPORTUNITY_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </Field>
          {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
          <button disabled={saving || !form.from_id || !form.to_id || !form.relationship_type} onClick={submitRelationship}
            className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white text-sm font-medium py-2 rounded-lg">
            {saving ? "Saving..." : "Add Relationship"}
          </button>
        </Modal>
      )}
    </div>
  );
}
