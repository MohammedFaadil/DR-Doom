import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/common/Button";
import type { Question } from "@/types/api";
import clsx from "clsx";

interface QuestionCardProps {
  question: Question;
  onAnswer: (args: { label: string; value: string | number | string[] }) => void;
  disabled?: boolean;
}

export function QuestionCard({ question, onAnswer, disabled }: QuestionCardProps) {
  const [selected, setSelected] = useState<string[]>([]);
  const [textValue, setTextValue] = useState("");
  const [numericValue, setNumericValue] = useState("");
  const [sliderValue, setSliderValue] = useState(5);

  const options = question.options || [];

  function toggleMulti(value: string) {
    setSelected((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  }

  function submitMulti() {
    if (!selected.length) return;
    const labels = options.filter((o) => selected.includes(o.value)).map((o) => o.label);
    onAnswer({ label: labels.join(", "), value: selected });
  }

  return (
    <div className="mt-3 rounded-2xl border border-brand-200 dark:border-brand-800 bg-brand-50/60 dark:bg-brand-950/30 p-4">
      <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-brand-600 dark:text-brand-400">
        Why I'm asking
      </p>
      <p className="mb-3 text-xs text-ink-500 dark:text-ink-400">{question.reason}</p>

      {question.type === "single_select" && (
        <div className="flex flex-wrap gap-2">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onAnswer({ label: opt.label, value: opt.value })}
              className="rounded-xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-3.5 py-2 text-sm font-medium text-ink-700 dark:text-ink-200 hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-950 transition-colors disabled:opacity-50"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {question.type === "yes_no" && (
        <div className="flex gap-2">
          {[
            { label: "Yes", value: "yes" },
            { label: "No", value: "no" },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onAnswer({ label: opt.label, value: opt.value })}
              className="rounded-xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-5 py-2 text-sm font-medium hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-950 transition-colors disabled:opacity-50"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {question.type === "multi_select" && (
        <div>
          <div className="flex flex-wrap gap-2">
            {options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                disabled={disabled}
                onClick={() => toggleMulti(opt.value)}
                className={clsx(
                  "rounded-xl border px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-50",
                  selected.includes(opt.value)
                    ? "border-brand-500 bg-brand-500 text-white"
                    : "border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 text-ink-700 dark:text-ink-200 hover:border-brand-400"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <Button size="sm" className="mt-3" disabled={disabled || !selected.length} onClick={submitMulti}>
            Continue
          </Button>
        </div>
      )}

      {question.type === "slider" && (
        <div>
          <input
            type="range"
            min={1}
            max={10}
            value={sliderValue}
            disabled={disabled}
            onChange={(e) => setSliderValue(Number(e.target.value))}
            className="w-full accent-brand-600"
          />
          <div className="mb-3 flex justify-between text-xs text-ink-500 dark:text-ink-400">
            <span>1 · Mild</span>
            <span className="font-semibold text-brand-600 dark:text-brand-400">{sliderValue}</span>
            <span>10 · Severe</span>
          </div>
          <Button size="sm" disabled={disabled} onClick={() => onAnswer({ label: `${sliderValue}/10`, value: sliderValue })}>
            Continue
          </Button>
        </div>
      )}

      {question.type === "numeric" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (numericValue.trim()) onAnswer({ label: numericValue.trim(), value: Number(numericValue) });
          }}
          className="flex gap-2"
        >
          <input
            type="number"
            disabled={disabled}
            value={numericValue}
            onChange={(e) => setNumericValue(e.target.value)}
            className="w-28 rounded-xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-400"
            autoFocus
          />
          <Button size="sm" type="submit" disabled={disabled || !numericValue.trim()}>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      )}

      {(question.type === "text" || question.type === "date") && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const value = textValue.trim() || "None";
            onAnswer({ label: value, value });
          }}
          className="flex gap-2"
        >
          <input
            type={question.type === "date" ? "date" : "text"}
            disabled={disabled}
            placeholder="Type your answer, or leave blank for none"
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
            className="flex-1 rounded-xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-400"
            autoFocus
          />
          <Button size="sm" type="submit" disabled={disabled}>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      )}
    </div>
  );
}
