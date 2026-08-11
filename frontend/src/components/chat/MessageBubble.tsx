import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Stethoscope, Volume2, VolumeX, AlertTriangle, ShieldCheck, Copy, Check } from "lucide-react";
import clsx from "clsx";
import { useVoice } from "@/hooks/useVoice";
import type { Citation, Question } from "@/types/api";
import { QuestionCard } from "@/components/chat/QuestionCard";
import { LoadingDots } from "@/components/common/LoadingDots";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  messageType?: string;
  question?: Question | null;
  evidence?: Citation[];
  isEmergency?: boolean;
  answered?: boolean;
  // True while tokens are still arriving from /api/chat/stream — shows a
  // typing cursor. The streamed text is already grounding-validated (see
  // backend/app/api/chat.py), so this is purely a progressive-reveal
  // effect, not an indicator that content might still change unsafely.
  streaming?: boolean;
  groundingConfidence?: number;
}

interface Props {
  message: DisplayMessage;
  onAnswer: (args: { label: string; value: string | number | string[] }) => void;
  answering: boolean;
}

export function MessageBubble({ message, onAnswer, answering }: Props) {
  const { ttsSupported, isSpeaking, speak, stopSpeaking } = useVoice();
  const [copied, setCopied] = useState(false);

  async function copyContent() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard permission denied — silently ignore, not critical */
    }
  }

  if (message.role === "user") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[80%] rounded-2xl rounded-tr-md bg-brand-600 px-4 py-2.5 text-sm text-white shadow-soft">
          {message.content}
        </div>
      </div>
    );
  }

  const isEmergency = message.isEmergency || message.messageType === "emergency";

  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl shadow-soft",
          isEmergency ? "bg-red-600 text-white" : "bg-brand-600 text-white"
        )}
      >
        {isEmergency ? <AlertTriangle className="h-4 w-4" /> : <Stethoscope className="h-4 w-4" />}
      </div>
      <div className="max-w-[85%] flex-1">
        <p className="mb-1 text-xs font-semibold text-ink-500 dark:text-ink-400">DR DOOM</p>
        <div
          className={clsx(
            "rounded-2xl rounded-tl-md border px-4 py-3 shadow-soft transition-shadow duration-300",
            !message.streaming && "hover:shadow-[0_4px_16px_-4px_rgba(15,23,42,0.14),0_12px_28px_-10px_rgba(15,23,42,0.14)]",
            isEmergency
              ? "border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/40"
              : "border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900"
          )}
        >
          {message.streaming && !message.content ? (
            <LoadingDots label="Thinking…" />
          ) : (
            <div className="prose-dr text-sm text-ink-800 dark:text-ink-100">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              {message.streaming && (
                <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-brand-500" />
              )}
            </div>
          )}

          {message.question && (
            <QuestionCard question={message.question} onAnswer={onAnswer} disabled={answering || message.answered} />
          )}
        </div>

        {(message.evidence?.length || ttsSupported || message.groundingConfidence !== undefined) && !message.streaming && (
          <div className="mt-1.5 flex flex-wrap items-center gap-3 px-1">
            {message.evidence && message.evidence.length > 0 && (
              <span className="text-[11px] font-medium text-ink-500 dark:text-ink-400">
                {message.evidence.length} source{message.evidence.length > 1 ? "s" : ""} cited
              </span>
            )}
            {message.groundingConfidence !== undefined && message.groundingConfidence > 0 && (
              <span
                className={clsx(
                  "inline-flex items-center gap-1 text-[11px] font-medium",
                  message.groundingConfidence >= 0.6
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-amber-600 dark:text-amber-400"
                )}
                title={`Grounding confidence: ${Math.round(message.groundingConfidence * 100)}% — how closely this answer matches the cited sources`}
              >
                <ShieldCheck className="h-3 w-3" />
                {Math.round(message.groundingConfidence * 100)}% grounded
              </span>
            )}
            {ttsSupported && message.content.length > 0 && (
              <button
                type="button"
                onClick={() => (isSpeaking ? stopSpeaking() : speak(message.content))}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-600 dark:text-brand-400 hover:underline"
              >
                {isSpeaking ? <VolumeX className="h-3 w-3" /> : <Volume2 className="h-3 w-3" />}
                {isSpeaking ? "Stop" : "Listen"}
              </button>
            )}
            {message.content.length > 0 && (
              <button
                type="button"
                onClick={copyContent}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-ink-500 hover:text-brand-600 hover:underline dark:text-ink-400 dark:hover:text-brand-400"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied" : "Copy"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
