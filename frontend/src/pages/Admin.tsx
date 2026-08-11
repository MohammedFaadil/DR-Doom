import { useEffect, useState } from "react";
import { Activity, Database, Gauge, MessageCircleWarning, ShieldCheck } from "lucide-react";
import { Card } from "@/components/common/Card";
import { api } from "@/services/api";

interface Overview {
  knowledge_base: { version: string; document_count: number; chunk_count: number; generated_at: string | null; index_ready: boolean };
  model: { provider: string; model_name: string; available: boolean };
  retrieval_metrics: { total_queries: number; avg_latency_ms: number; avg_grounding_score: number; grounding_failures: number };
  feedback: { total: number; positive: number; positive_rate: number | null };
  config: Record<string, unknown>;
}

export function Admin() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Overview>("/api/admin/overview")
      .then(setData)
      .catch(() => setError("Admin access required, or the overview failed to load."));
  }, []);

  if (error) return <div className="flex-1 p-10 text-sm text-red-500">{error}</div>;
  if (!data) return <div className="flex-1 p-10 text-sm text-ink-400">Loading diagnostics…</div>;

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin pb-24 md:pb-0">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="mb-1 text-2xl font-bold text-ink-900 dark:text-white">Admin diagnostics</h1>
        <p className="mb-8 text-sm text-ink-500 dark:text-ink-400">Live system health — no patient content shown.</p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={Database} label="Knowledge base" value={`${data.knowledge_base.chunk_count} chunks`} sub={`${data.knowledge_base.document_count} documents · v${data.knowledge_base.version}`} good={data.knowledge_base.index_ready} />
          <StatCard icon={ShieldCheck} label="Model provider" value={data.model.provider} sub={data.model.model_name} good={data.model.available} />
          <StatCard icon={Gauge} label="Avg retrieval latency" value={`${data.retrieval_metrics.avg_latency_ms} ms`} sub={`${data.retrieval_metrics.total_queries} total queries`} good />
          <StatCard icon={Activity} label="Avg grounding score" value={data.retrieval_metrics.avg_grounding_score.toFixed(2)} sub={`${data.retrieval_metrics.grounding_failures} grounding failures`} good={data.retrieval_metrics.grounding_failures === 0} />
        </div>

        <Card className="mt-6 p-6">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-800 dark:text-ink-100">
            <MessageCircleWarning className="h-4 w-4" /> User feedback
          </h2>
          <p className="text-sm text-ink-600 dark:text-ink-300">
            {data.feedback.total} responses ·{" "}
            {data.feedback.positive_rate != null ? `${Math.round(data.feedback.positive_rate * 100)}% positive` : "no data yet"}
          </p>
        </Card>

        <Card className="mt-6 p-6">
          <h2 className="mb-3 text-sm font-semibold text-ink-800 dark:text-ink-100">Runtime configuration</h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
            {Object.entries(data.config).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-ink-100 dark:border-ink-800 py-1">
                <dt className="text-ink-500">{k}</dt>
                <dd className="font-mono text-ink-700 dark:text-ink-300">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  good,
}: {
  icon: typeof Database;
  label: string;
  value: string;
  sub: string;
  good?: boolean;
}) {
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <Icon className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        <span className={`h-2 w-2 rounded-full ${good ? "bg-brand-500" : "bg-red-500"}`} />
      </div>
      <p className="text-lg font-bold text-ink-900 dark:text-white">{value}</p>
      <p className="text-xs text-ink-500 dark:text-ink-400">{label}</p>
      <p className="mt-0.5 text-[10px] text-ink-400">{sub}</p>
    </Card>
  );
}
