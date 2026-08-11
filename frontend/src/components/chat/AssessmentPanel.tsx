import { ClipboardList, ExternalLink } from "lucide-react";
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
}

export function AssessmentPanel({ patientState, riskLevel, evidence }: Props) {
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

      <Card className="p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
          Evidence ({evidence.length})
        </p>
        {evidence.length === 0 ? (
          <p className="text-sm text-ink-400">No sources retrieved yet</p>
        ) : (
          <ul className="space-y-2">
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
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
