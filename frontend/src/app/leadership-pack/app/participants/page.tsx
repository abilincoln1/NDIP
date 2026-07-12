"use client";
import { useEffect, useState } from "react";
import { PageHeader, StatCard, Spinner, Badge, EmptyState } from "@/components/ui";
import { participantsApi } from "@/lib/api";
import { Users, Globe, Briefcase } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { analyticsApi } from "@/lib/api";

export default function ParticipantsPage() {
  const [participants, setParticipants] = useState<any[]>([]);
  const [count, setCount] = useState(0);
  const [geo, setGeo] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [country, setCountry] = useState("");
  const [profession, setProfession] = useState("");

  const load = () => {
    setLoading(true);
    Promise.all([
      participantsApi.list({ country: country || undefined, profession: profession || undefined }),
      participantsApi.count(),
      analyticsApi.geography(),
    ])
      .then(([p, c, g]) => {
        setParticipants(p.data);
        setCount(c.data.total);
        setGeo(g.data.countries?.slice(0, 10) || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader title="Participants" subtitle="Opt-in registrant directory — no individual profiling" />

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <StatCard label="Total registrants" value={count.toLocaleString()} icon={<Users size={18} />} color="blue" />
        <StatCard label="Countries represented" value={geo.length} icon={<Globe size={18} />} color="teal" />
        <StatCard label="Showing" value={participants.length} icon={<Briefcase size={18} />} sub="Filtered results" color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Geographic bar chart */}
        <div className="card lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Top countries by registrant count</h2>
          {geo.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={geo} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis type="category" dataKey="country" tick={{ fill: "#94a3b8", fontSize: 11 }} width={80} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyState message="No geographic data yet." />}
        </div>

        {/* Filters */}
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Filter directory</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Country</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                placeholder="e.g. Nigeria"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Profession</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                placeholder="e.g. Engineer"
                value={profession}
                onChange={(e) => setProfession(e.target.value)}
              />
            </div>
            <button
              onClick={load}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-2 text-sm font-medium transition-colors"
            >
              Apply filters
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Registrant directory</h2>
          <span className="text-xs text-slate-500">{participants.length} results</span>
        </div>
        {loading ? (
          <Spinner />
        ) : participants.length === 0 ? (
          <EmptyState message="No participants match these filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/50">
                <tr>
                  {["ID", "Country", "City", "Profession", "Skills", "Joined"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs text-slate-500 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {participants.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">#{p.id}</td>
                    <td className="px-4 py-3 text-slate-200">{p.country || "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{p.city || "—"}</td>
                    <td className="px-4 py-3 text-slate-200">{p.profession || "—"}</td>
                    <td className="px-4 py-3">
                      {p.skills
                        ? p.skills.split(",").slice(0, 3).map((s: string) => (
                            <Badge key={s} variant="gray">{s.trim()}</Badge>
                          ))
                        : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
