import { useState } from "react";
import { Download, RotateCcw, PlusCircle, ThumbsUp, ThumbsDown, Stethoscope } from "lucide-react";
import clsx from "clsx";
import { Button } from "@/components/common/Button";
import { API_URL } from "@/services/api";
import { api } from "@/services/api";
import type { ConsultationSummary } from "@/types/api";

interface Props {
  conversationId: string;
  summary?: ConsultationSummary | null;
  onNewConsultation: () => void;
}

const RISK_STYLES: Record<string, string> = {
  emergency: "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200",
  urgent: "border-red-200 bg-red-50/70 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300",
  moderate: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200",
  low: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200",
  unknown: "border-ink-200 bg-ink-50 text-ink-700 dark:border-ink-800 dark:bg-ink-800/60 dark:text-ink-200",
};

export function SummaryActions({ conversationId, summary, onNewConsultation }: Props) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  async function sendFeedback(helpful: boolean) {
    setFeedback(helpful ? "up" : "down");
    try {
      await api.post("/api/feedback", { conversation_id: conversationId, was_helpful: helpful });
    } catch {
      /* best-effort */
    }
  }

  const nextStep = summary?.recommended_next_step;
  const riskTone = RISK_STYLES[summary?.risk_level ?? "unknown"] ?? RISK_STYLES.unknown;

  return (
    <div className="mt-4 space-y-3">
      {nextStep && (
        <div className={clsx("flex items-start gap-3 rounded-2xl border p-4 shadow-soft", riskTone)}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/60 dark:bg-black/20">
            <Stethoscope className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide opacity-80">Recommended next step</p>
            <p className="mt-0.5 text-sm font-medium leading-relaxed">{nextStep}</p>
          </div>
        </div>
      )}

      <div className="space-y-3 rounded-2xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-4 shadow-soft">
        <div className="flex flex-wrap gap-2">
          {summary?.id && (
            <a href={`${API_URL}/api/summaries/${summary.id}/pdf`} target="_blank" rel="noreferrer">
              <Button size="sm" variant="outline" className="gap-1.5">
                <Download className="h-3.5 w-3.5" /> Download PDF
              </Button>
            </a>
          )}
          <Button size="sm" variant="outline" className="gap-1.5" onClick={onNewConsultation}>
            <PlusCircle className="h-3.5 w-3.5" /> Start new assessment
          </Button>
          <Button size="sm" variant="ghost" className="gap-1.5">
            <RotateCcw className="h-3.5 w-3.5" /> Continue conversation
          </Button>
        </div>

        <div className="flex items-center gap-3 border-t border-ink-100 dark:border-ink-800 pt-3">
          <span className="text-xs text-ink-500 dark:text-ink-400">Was this helpful?</span>
          <button
            type="button"
            onClick={() => sendFeedback(true)}
            className={`rounded-lg p-1.5 ${feedback === "up" ? "bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-300" : "text-ink-400 hover:bg-ink-100 dark:hover:bg-ink-800"}`}
          >
            <ThumbsUp className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => sendFeedback(false)}
            className={`rounded-lg p-1.5 ${feedback === "down" ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300" : "text-ink-400 hover:bg-ink-100 dark:hover:bg-ink-800"}`}
          >
            <ThumbsDown className="h-4 w-4" />
          </button>
          {feedback && <span className="text-xs text-ink-400">Thanks for the feedback</span>}
        </div>
      </div>
    </div>
  );
}
