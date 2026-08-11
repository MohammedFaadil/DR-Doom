import clsx from "clsx";

const STYLES: Record<string, string> = {
  emergency: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300 ring-1 ring-red-300 dark:ring-red-800",
  urgent: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300 ring-1 ring-orange-300 dark:ring-orange-800",
  moderate: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 ring-1 ring-amber-300 dark:ring-amber-800",
  low: "bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-300 ring-1 ring-brand-300 dark:ring-brand-800",
  unknown: "bg-ink-100 text-ink-500 dark:bg-ink-800 dark:text-ink-400 ring-1 ring-ink-200 dark:ring-ink-700",
};

export function RiskBadge({ level }: { level: string }) {
  const key = (level || "unknown").toLowerCase();
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide", STYLES[key] || STYLES.unknown)}>
      {key}
    </span>
  );
}
