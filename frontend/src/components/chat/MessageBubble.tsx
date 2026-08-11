import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Stethoscope, Volume2, VolumeX, AlertTriangle } from "lucide-react";
import clsx from "clsx";
import { useVoice } from "@/hooks/useVoice";
import type { Citation, Question } from "@/types/api";
import { QuestionCard } from "@/components/chat/QuestionCard";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  messageType?: string;
  question?: Question | null;
  evidence?: Citation[];
  isEmergency?: boolean;
  answered?: boolean;
}

interface Props {
  message: DisplayMessage;
  onAnswer: (args: { label: string; value: string | number | string[] }) => void;
  answering: boolean;
}

export function MessageBubble({ message, onAnswer, answering }: Props) {
  const { ttsSupported, isSpeaking, speak, stopSpeaking } = useVoice();

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
            "rounded-2xl rounded-tl-md border px-4 py-3 shadow-soft",
            isEmergency
              ? "border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/40"
              : "border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900"
          )}
        >
          <div className="prose-dr text-sm text-ink-800 dark:text-ink-100">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>

          {message.question && (
            <QuestionCard question={message.question} onAnswer={onAnswer} disabled={answering || message.answered} />
          )}
        </div>

        {(message.evidence?.length || ttsSupported) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-3 px-1">
            {message.evidence && message.evidence.length > 0 && (
              <span className="text-[11px] font-medium text-ink-500 dark:text-ink-400">
                {message.evidence.length} source{message.evidence.length > 1 ? "s" : ""} cited
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
          </div>
        )}
      </div>
    </div>
  );
}
