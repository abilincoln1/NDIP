"use client";
import { useEffect, useState } from "react";
import { dataHealthApi } from "@/lib/api";
import { PageHeader, StatCard, Spinner, Badge, EmptyState } from "@/components/ui";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { CheckCircle, XCircle, AlertCircle, Clock } from "lucide-react";

const statusIcon = (s: string) => {
  if (s === "ok") return <CheckCircle size={14} className="text-teal-400" />;
  if (s === "error") return <XCircle size={14} className="text-red-400" />;
  if (s === "not_configured" || s === "unconfigured" || s === "never_run") return <AlertCircle size={14} className="text-slate-500" />;
  return <Clock size={14} className="text-amber-400" />;
};

const statusBadge = (s: string) => {
  if (s === "ok") return <Badge variant="green">OK</Badge>;
  if (s === "error") return <Badge variant="red">Error</Badge>;
  if (s === "not_configured" || s === "unconfigured") return <Badge variant="gray">Not configured</Badge>;
  return <Badge variant="amber">{s}</Badge>;
};

export default function DataHealthPage() {
  const [overview, setOverview] = useState<any>(null);
  const [connectors, setConnectors] = useState<any[]>([]);
  const [volume, setVolume] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      dataHealthApi.overview(),
      dataHealthApi.connectors(24),
      dataHealthApi.ingestionVolume(30),
      dataHealthApi.jobs(10),
      dataHealthApi.errors(24),
    ]).then(([ov, cn, vol, jb, err]) => {
      setOverview(ov.data);
      setConnectors(cn.data.connectors || []);
      setVolume(vol.data.volume || []);
      setJobs(jb.data.jobs || []);
      setErrors(err.data.errors || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div>
      <PageHeader title="Data Health" subtitle="Connector status, ingestion monitoring, pipeline health" />

      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Connectors active" value={`${overview.connectors_configured}/${overview.connectors_total}`} color="blue" />
          <StatCard label="Health score" value={`${overview.connector_health_pct}%`} color={overview.connector_health_pct > 50 ? "teal" : "red"} />
          <StatCard label="Normalisation rate" value={`${overview.normalisation?.normalisation_rate}%`} color="purple" />
          <StatCard label="Data fresh" value={overview.data_fresh ? "Yes" : "No"} color={overview.data_fresh ? "teal" : "amber"} sub={overview.latest_post_fetched ? new Date(overview.latest_post_fetched).toLocaleDateString() : "Never"} />
        </div>
      )}

      {/* Ingestion volume chart */}
      <div className="card mb-6">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Ingestion volume (30 days)</h2>
        {volume.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={volume}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyState message="No ingestion data yet." />}
      </div>

      {/* Connector health table */}
      <div className="card mb-6 p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-300">Connector health</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/50">
              <tr>
                {["Platform", "Type", "Status", "Configured", "Fetched 24h", "New 24h", "Errors"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {connectors.map((c: any) => (
                <tr key={c.platform} className="hover:bg-slate-800/30">
                  <td className="px-4 py-3 text-slate-200 capitalize">{c.platform.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3"><Badge variant="gray">{c.type}</Badge></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {statusIcon(c.last_status)}
                      {statusBadge(c.last_status)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {c.configured ? <Badge variant="green">Yes</Badge> : <Badge variant="gray">No</Badge>}
                  </td>
                  <td className="px-4 py-3 text-slate-400 tabular-nums">{c.total_fetched_24h}</td>
                  <td className="px-4 py-3 text-slate-400 tabular-nums">{c.total_new_24h}</td>
                  <td className="px-4 py-3">
                    {c.error_count > 0 ? <Badge variant="red">{c.error_count}</Badge> : <span className="text-slate-600">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent jobs */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-300">Recent ingest jobs</h2>
          </div>
          {jobs.length === 0 ? <EmptyState message="No jobs yet." /> : (
            <div className="divide-y divide-slate-800">
              {jobs.map((j: any) => (
                <div key={j.id} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-slate-200 truncate max-w-[180px]">{j.query}</span>
                    {j.status === "completed" ? <Badge variant="green">Done</Badge> : <Badge variant="amber">{j.status}</Badge>}
                  </div>
                  <div className="flex gap-3 text-xs text-slate-500">
                    <span>{j.total_fetched} fetched</span>
                    <span>{j.total_new} new</span>
                    <span>{new Date(j.started_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent errors */}
        <div className="card p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-300">Recent errors (24h)</h2>
          </div>
          {errors.length === 0 ? (
            <div className="p-6 flex items-center gap-2 text-teal-400">
              <CheckCircle size={16} /> <span className="text-sm">No errors in last 24 hours</span>
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {errors.map((e: any, i: number) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant="red">{e.platform}</Badge>
                    <span className="text-xs text-slate-500">{new Date(e.checked_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">{e.error}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
