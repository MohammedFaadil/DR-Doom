import { useState } from "react";
import { Download, RotateCcw, PlusCircle, ThumbsUp, ThumbsDown } from "lucide-react";
import { Button } from "@/components/common/Button";
import { API_URL } from "@/services/api";
import { api } from "@/services/api";

interface Props {
  conversationId: string;
  summaryId?: string;
  onNewConsultation: () => void;
}

export function SummaryActions({ conversationId, summaryId, onNewConsultation }: Props) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  async function sendFeedback(helpful: boolean) {
    setFeedback(helpful ? "up" : "down");
    try {
      await api.post("/api/feedback", { conversation_id: conversationId, was_helpful: helpful });
    } catch {
      /* best-effort */
    }
  }

  return (
    <div className="mt-4 space-y-3 rounded-2xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-4 shadow-soft">
      <div className="flex flex-wrap gap-2">
        {summaryId && (
          <a href={`${API_URL}/api/summaries/${summaryId}/pdf`} target="_blank" rel="noreferrer">
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
  );
}
