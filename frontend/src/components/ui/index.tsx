import clsx from "clsx";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { ReactNode } from "react";

// ─── Stat card ────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  trend?: number;  // positive = up, negative = down
  icon?: ReactNode;
  color?: "blue" | "teal" | "amber" | "red" | "purple";
}

const COLOR_MAP = {
  blue:   "text-blue-400",
  teal:   "text-teal-400",
  amber:  "text-amber-400",
  red:    "text-red-400",
  purple: "text-purple-400",
};

export function StatCard({ label, value, sub, trend, icon, color = "blue" }: StatCardProps) {
  const TrendIcon = trend === undefined ? null : trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;
  const trendColor = trend && trend > 0 ? "text-teal-400" : trend && trend < 0 ? "text-red-400" : "text-slate-500";

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</span>
        {icon && <span className={clsx("opacity-60", COLOR_MAP[color])}>{icon}</span>}
      </div>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold text-white tabular-nums">{value}</span>
        {TrendIcon && trend !== undefined && (
          <span className={clsx("flex items-center gap-0.5 text-xs mb-1", trendColor)}>
            <TrendIcon size={12} />
            {Math.abs(trend * 100).toFixed(1)}%
          </span>
        )}
      </div>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-bold text-white">{title}</h1>
      {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
    </div>
  );
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={clsx("animate-pulse bg-slate-800 rounded", className)} />
  );
}

// ─── Badge ────────────────────────────────────────────────────────────────────
interface BadgeProps { children: ReactNode; variant?: "blue" | "green" | "red" | "amber" | "gray" }
const BADGE_VARIANTS = {
  blue:  "bg-blue-500/20 text-blue-300",
  green: "bg-teal-500/20 text-teal-300",
  red:   "bg-red-500/20  text-red-300",
  amber: "bg-amber-500/20 text-amber-300",
  gray:  "bg-slate-700 text-slate-300",
};
export function Badge({ children, variant = "gray" }: BadgeProps) {
  return (
    <span className={clsx("badge", BADGE_VARIANTS[variant])}>{children}</span>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-500">
      <Minus size={32} className="mb-3 opacity-40" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ─── Loading spinner ──────────────────────────────────────────────────────────
export function Spinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
