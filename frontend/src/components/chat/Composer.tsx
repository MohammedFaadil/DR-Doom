import { FormEvent, useEffect, useState } from "react";
import { Mic, Send, Square } from "lucide-react";
import clsx from "clsx";
import { useVoice } from "@/hooks/useVoice";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function Composer({ onSend, disabled, placeholder }: Props) {
  const [text, setText] = useState("");
  const { sttSupported, isListening, transcript, startListening, stopListening } = useVoice();

  useEffect(() => {
    if (transcript) setText(transcript);
  }, [transcript]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  }

  return (
    <form onSubmit={submit} className="flex items-end gap-2">
      <div className="flex flex-1 items-center gap-2 rounded-2xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 shadow-soft focus-within:ring-2 focus-within:ring-brand-400">
        <input
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder || "Describe what you're experiencing…"}
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-ink-400 disabled:opacity-60"
        />
        {sttSupported && (
          <button
            type="button"
            title={isListening ? "Stop recording" : "Press and hold to speak"}
            onClick={() => (isListening ? stopListening() : startListening())}
            className={clsx(
              "flex h-8 w-8 items-center justify-center rounded-full transition-colors",
              isListening ? "bg-red-500 text-white animate-pulse-ring" : "text-ink-400 hover:bg-ink-100 dark:hover:bg-ink-800"
            )}
          >
            {isListening ? <Square className="h-3.5 w-3.5" /> : <Mic className="h-4 w-4" />}
          </button>
        )}
      </div>
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft transition-transform hover:bg-brand-700 disabled:opacity-40 active:scale-95"
      >
        <Send className="h-4 w-4" />
      </button>
    </form>
  );
}
