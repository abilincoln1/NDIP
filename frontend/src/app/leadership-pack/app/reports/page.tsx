"use client";
import { useEffect, useState } from "react";
import { PageHeader, Spinner, Badge, EmptyState } from "@/components/ui";
import { reportsApi } from "@/lib/api";
import { FileText, Download, Plus, Calendar } from "lucide-react";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({
    period: "weekly",
    period_start: "",
    period_end: "",
    title: "",
  });
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    reportsApi.list().then((r) => setReports(r.data)).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const generate = async () => {
    if (!form.period_start || !form.period_end) return;
    setGenerating(true);
    try {
      await reportsApi.generate({
        ...form,
        period_start: new Date(form.period_start).toISOString(),
        period_end: new Date(form.period_end).toISOString(),
      });
      setShowForm(false);
      load();
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const download = (report: any) => {
    const blob = new Blob([report.content_json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agora-report-${report.id}.json`;
    a.click();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Reports</h1>
          <p className="text-sm text-slate-400 mt-1">Neutral, factual, aggregated summaries</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          <Plus size={14} />
          Generate report
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">New report</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Period type</label>
              <select
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                value={form.period}
                onChange={(e) => setForm({ ...form, period: e.target.value })}
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Start date</label>
              <input
                type="date"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                value={form.period_start}
                onChange={(e) => setForm({ ...form, period_start: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">End date</label>
              <input
                type="date"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                value={form.period_end}
                onChange={(e) => setForm({ ...form, period_end: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Title (optional)</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                placeholder="Auto-generated if blank"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              onClick={generate}
              disabled={generating}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium"
            >
              {generating ? "Generating..." : "Generate"}
            </button>
            <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-200 text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <Spinner />
      ) : reports.length === 0 ? (
        <EmptyState message="No reports generated yet." />
      ) : (
        <div className="space-y-3">
          {reports.map((r) => {
            const content = (() => { try { return JSON.parse(r.content_json); } catch { return null; } })();
            return (
              <div key={r.id} className="card flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 p-2 bg-blue-500/10 rounded-lg">
                    <FileText size={16} className="text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{r.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="blue">{r.period}</Badge>
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Calendar size={10} />
                        {new Date(r.period_start).toLocaleDateString()} – {new Date(r.period_end).toLocaleDateString()}
                      </span>
                    </div>
                    {content?.summary && (
                      <div className="flex gap-4 mt-2">
                        {[
                          ["Participants", content.summary.total_participants],
                          ["Engagements", content.summary.total_engagements],
                          ["Events", content.summary.events_held],
                        ].map(([l, v]) => (
                          <div key={l as string}>
                            <p className="text-xs text-slate-500">{l}</p>
                            <p className="text-sm font-semibold text-white tabular-nums">{v}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    {content?.anomalies?.length > 0 && (
                      <div className="mt-2">
                        {content.anomalies.map((a: string, i: number) => (
                          <p key={i} className="text-xs text-amber-400">⚠ {a}</p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => download(r)}
                  className="shrink-0 flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition-colors"
                >
                  <Download size={12} />
                  JSON
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
