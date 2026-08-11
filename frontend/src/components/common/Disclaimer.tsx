import { ShieldAlert } from "lucide-react";

export function Disclaimer({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <p className="text-[11px] text-ink-500 dark:text-ink-400 leading-relaxed">
        Dr Doom provides educational health information, not a diagnosis. If symptoms are severe or concerning,
        seek medical care.
      </p>
    );
  }
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/40 p-4 text-amber-900 dark:text-amber-200">
      <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5" />
      <p className="text-sm leading-relaxed">
        Dr Doom provides AI-generated health information and educational guidance based on its available medical
        knowledge sources. It is <strong>not a substitute</strong> for an examination, diagnosis, or treatment from a
        qualified healthcare professional. If symptoms are severe, sudden, or concerning, seek appropriate medical
        care immediately.
      </p>
    </div>
  );
}
