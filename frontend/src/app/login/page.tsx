"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";

// NDIP brand mark — pulse/signal line above the NDIP letters, inside a
// rounded teal square. Same geometry as the sidebar mark, scaled up.
function NdipLogo({ size = 56 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 180 180" aria-hidden="true">
      <rect x="0" y="0" width="180" height="180" rx="28" fill="#0C7A63" />
      <path
        d="M 22 69 L 48 69 L 60 47 L 76 87 L 92 51 L 106 69 L 158 69"
        fill="none" stroke="#FFFFFF" strokeWidth="7"
        strokeLinecap="round" strokeLinejoin="round"
      />
      <circle cx="92" cy="51" r="7" fill="#F2B33D" />
      <text
        x="90" y="133" textAnchor="middle"
        fontFamily="Arial, sans-serif" fontSize="44" fontWeight="500"
        letterSpacing="1" fill="#FFFFFF"
      >
        NDIP
      </text>
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await authApi.login(email, password);
      localStorage.setItem("agora_token", r.data.access_token);
      router.push("/");
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Invalid credentials. Check your email and password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-8">
          <NdipLogo size={56} />
          <div className="text-center">
            <p className="text-lg font-bold text-white">National & Diaspora Intelligence Platform (NDIP)</p>
            <p className="text-xs text-slate-400">Understanding Nigeria. Understanding the Diaspora.</p>
            <p className="text-xs text-slate-600 mt-0.5">Powered by RTIFN</p>
          </div>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <h1 className="text-base font-semibold text-white mb-2">Sign in</h1>
          {error && <p className="text-xs text-red-400 bg-red-500/10 rounded-lg px-3 py-2">{error}</p>}
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Email</label>
            <input
              type="email" required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              value={email} onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Password</label>
            <input
              type="password" required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              value={password} onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button
            type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
