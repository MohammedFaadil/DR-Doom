import { ClipboardList, ExternalLink, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { Card } from "@/components/common/Card";
import { RiskBadge } from "@/components/common/RiskBadge";
import type { Citation } from "@/types/api";

interface PatientStateShape {
  age?: number | null;
  sex?: string | null;
  symptoms?: { name: string; duration?: string | null; severity?: number | null }[];
  missing_information?: string[];
}

interface Props {
  patientState: PatientStateShape;
  riskLevel: string;
  evidence: Citation[];
  groundingConfidence?: number;
}

export function AssessmentPanel({ patientState, riskLevel, evidence, groundingConfidence }: Props) {
  const symptoms = patientState.symptoms || [];

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto scrollbar-thin p-5">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink-800 dark:text-ink-100">
        <ClipboardList className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        Assessment
      </div>

      <Card className="p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
          Patient profile
        </p>
        <div className="space-y-1 text-sm text-ink-700 dark:text-ink-200">
          <p>Age: {patientState.age ?? "Not provided"}</p>
          <p>Sex: {patientState.sex ?? "Not provided"}</p>
        </div>
      </Card>

      <Card className="p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
          Symptoms detected
        </p>
        {symptoms.length === 0 ? (
          <p className="text-sm text-ink-400">None yet</p>
        ) : (
          <ul className="space-y-1.5 text-sm text-ink-700 dark:text-ink-200">
            {symptoms.map((s) => (
              <li key={s.name} className="flex items-center justify-between">
                <span className="capitalize">{s.name}</span>
                <span className="text-xs text-ink-400">
                  {s.duration ? s.duration : ""} {s.severity != null ? `· ${s.severity}/10` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">Risk level</p>
        <RiskBadge level={riskLevel} />
        <p className="mt-2 text-[11px] text-ink-500 dark:text-ink-400">
          An educational triage indicator, not a diagnosis.
        </p>
      </Card>

      {groundingConfidence !== undefined && groundingConfidence > 0 && (
        <Card className="p-4">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
            <ShieldCheck className="h-3.5 w-3.5" /> Grounding confidence
          </p>
          <div className="mb-1.5 h-2 w-full overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
            <div
              className={clsx(
                "h-full rounded-full transition-all",
                groundingConfidence >= 0.6 ? "bg-emerald-500" : "bg-amber-500"
              )}
              style={{ width: `${Math.round(groundingConfidence * 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-ink-500 dark:text-ink-400">
            {Math.round(groundingConfidence * 100)}% of the last answer's claims matched cited sources closely — the
            rest was automatically removed rather than shown unverified.
          </p>
        </Card>
      )}

      <Card className="p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
          Evidence ({evidence.length})
        </p>
        {evidence.length === 0 ? (
          <p className="text-sm text-ink-400">No sources retrieved yet</p>
        ) : (
          <ul className="space-y-2.5">
            {evidence.map((e, i) => (
              <li key={`${e.url}-${i}`}>
                <a
                  href={e.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start gap-1.5 text-xs text-brand-600 dark:text-brand-400 hover:underline"
                >
                  <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
                  <span>
                    {e.organization} — {e.title}
                  </span>
                </a>
                {e.score !== undefined && e.score > 0 && (
                  <div className="mt-1 flex items-center gap-1.5 pl-4.5">
                    <div className="h-1 w-16 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
                      <div
                        className="h-full rounded-full bg-brand-400"
                        style={{ width: `${Math.round(Math.min(e.score, 1) * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-ink-400">{Math.round(Math.min(e.score, 1) * 100)}% relevant</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
