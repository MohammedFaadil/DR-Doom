import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  MessageSquarePlus,
  History,
  User,
  FileText,
  Stethoscope,
  ArrowRight,
  ClipboardList,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Activity,
  Sparkles,
  ShieldCheck,
  Lightbulb,
  Mic,
} from "lucide-react";
import { Card } from "@/components/common/Card";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Reveal } from "@/components/common/Reveal";
import { useAuthStore } from "@/stores/authStore";
import { useVoice } from "@/hooks/useVoice";
import { conversationsApi, ConversationStats } from "@/services/conversations";
import type { ConversationCard } from "@/types/api";

// General wellness tips — clearly generic public-health reminders, never
// framed as personalized advice (that only ever comes from a grounded
// consultation). Rotates deterministically by day-of-year so it's stable
// across re-renders/refreshes within the same day, not random per-render.
const WELLNESS_TIPS = [
  "Adults typically need 7-9 hours of sleep — consistent sleep and wake times matter as much as total hours.",
  "Aim for at least 2 liters of water a day, more if it's hot or you're active — thirst is a lagging signal.",
  "Hand-washing for 20 seconds is still one of the most effective ways to avoid common infections.",
  "Regular movement — even a 10-minute walk — measurably helps mood and cardiovascular health.",
  "Annual check-ups catch problems early, even when you feel completely fine.",
  "Screen time before bed can delay sleep onset — a short wind-down routine helps.",
  "Most colds resolve in 7-10 days; symptoms lasting longer or worsening are worth a second look.",
  "Reading medication labels fully — including interactions — takes a minute and prevents most avoidable errors.",
];

function tipOfTheDay(): string {
  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86_400_000
  );
  return WELLNESS_TIPS[dayOfYear % WELLNESS_TIPS.length];
}

const QUICK_ACTIONS = [
  {
    to: "/app/chat",
    label: "Start consultation",
    desc: "Describe symptoms and get a grounded assessment",
    icon: MessageSquarePlus,
    primary: true,
  },
  { to: "/app/history", label: "View history", desc: "Revisit past consultations", icon: History },
  { to: "/app/profile", label: "Health profile", desc: "Keep your details up to date", icon: User },
  { to: "/app/history", label: "Saved summaries", desc: "Export or share as PDF", icon: FileText },
];

const SUGGESTIONS = [
  "I've had a headache since this morning",
  "What causes migraines?",
  "I have a sore throat and fever",
  "Tell me about ibuprofen",
];

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function relativeDate(iso: string): string {
  const then = new Date(iso).getTime();
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function Dashboard() {
  const { user } = useAuthStore();
  const { sttSupported, ttsSupported } = useVoice();
  const [recent, setRecent] = useState<ConversationCard[]>([]);
  const [stats, setStats] = useState<ConversationStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([conversationsApi.list(), conversationsApi.stats()])
      .then(([rows, s]) => {
        setRecent(rows.slice(0, 5));
        setStats(s);
      })
      .catch(() => {
        /* dashboard degrades to empty state */
      })
      .finally(() => setLoading(false));
  }, []);

  const firstName = user?.full_name?.split(" ")[0];

  const statCards = [
    { label: "Consultations", value: stats?.total_consultations ?? 0, icon: ClipboardList, tone: "text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950/60" },
    { label: "Completed", value: stats?.completed ?? 0, icon: CheckCircle2, tone: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60" },
    { label: "In progress", value: stats?.in_progress ?? 0, icon: Clock, tone: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60" },
    { label: "Urgent flagged", value: stats?.urgent_flagged ?? 0, icon: AlertTriangle, tone: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/60" },
  ];

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin pb-24 md:pb-0">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* ── Header ─────────────────────────────── */}
        <div className="animate-fade-up">
          <p className="text-sm text-ink-500 dark:text-ink-400">{greeting()}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink-900 dark:text-white">
            {firstName ? `Welcome back, ${firstName}` : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-ink-500 dark:text-ink-400">
            {stats?.last_consultation_at
              ? `Your last consultation was ${relativeDate(stats.last_consultation_at).toLowerCase()}.`
              : "Start your first consultation whenever you're ready."}
          </p>
        </div>

        {/* ── Hero CTA ───────────────────────────── */}
        <Reveal className="mt-8">
          <Link to="/app/chat">
            <div className="group relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-7 shadow-xl shadow-brand-900/15 transition-transform duration-300 hover:-translate-y-0.5 sm:p-9">
              <div className="pointer-events-none absolute -right-10 -top-16 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
              <div className="pointer-events-none absolute -bottom-20 left-10 h-44 w-44 rounded-full bg-brand-300/20 blur-3xl" />
              <div className="relative flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-center">
                <div>
                  <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-[11px] font-semibold text-white backdrop-blur">
                    <Sparkles className="h-3 w-3" /> Evidence-grounded
                  </div>
                  <h2 className="text-2xl font-bold text-white sm:text-3xl">
                    How can I help you today?
                  </h2>
                  <p className="mt-2 max-w-md text-sm text-brand-50/90">
                    Describe what you're experiencing and I'll ask focused clinical questions before
                    giving you cited guidance.
                  </p>
                </div>
                <span className="inline-flex shrink-0 items-center gap-2 rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-brand-700 shadow-lg transition-transform group-hover:scale-105">
                  Start consultation
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
              </div>
            </div>
          </Link>
        </Reveal>

        {/* ── Stats ──────────────────────────────── */}
        <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {statCards.map((s, i) => (
            <Reveal key={s.label} delay={i * 70}>
              <Card className="lift p-4">
                <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl ${s.tone}`}>
                  <s.icon className="h-4 w-4" />
                </div>
                <p className="text-2xl font-bold text-ink-900 dark:text-white">
                  {loading ? "—" : s.value}
                </p>
                <p className="text-xs text-ink-500 dark:text-ink-400">{s.label}</p>
              </Card>
            </Reveal>
          ))}
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* ── Main column ─────────────────────── */}
          <div className="lg:col-span-2">
            <Reveal>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
                  Recent consultations
                </h2>
                <Link to="/app/history" className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline">
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>

              {loading ? (
                <div className="space-y-3">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-[68px] animate-pulse rounded-2xl bg-ink-100 dark:bg-ink-800" />
                  ))}
                </div>
              ) : recent.length === 0 ? (
                <Card className="flex flex-col items-center gap-3 p-12 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 dark:bg-brand-950">
                    <Stethoscope className="h-6 w-6 text-brand-500" />
                  </div>
                  <div>
                    <p className="font-medium text-ink-700 dark:text-ink-200">No consultations yet</p>
                    <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">
                      Your consultations and summaries will appear here.
                    </p>
                  </div>
                  <Link to="/app/chat" className="text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline">
                    Start your first consultation →
                  </Link>
                </Card>
              ) : (
                <div className="space-y-3">
                  {recent.map((c, i) => (
                    <Reveal key={c.id} delay={i * 60}>
                      <Link to={`/app/chat/${c.id}`}>
                        <Card className="lift flex items-center gap-4 p-4">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 dark:bg-brand-950 text-brand-600 dark:text-brand-400">
                            <Activity className="h-4.5 w-4.5" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-ink-800 dark:text-ink-100">
                              {c.title}
                            </p>
                            <p className="mt-0.5 text-xs text-ink-500 dark:text-ink-400">
                              {relativeDate(c.updated_at)}
                              {c.is_complete ? " · Complete" : " · In progress"}
                            </p>
                          </div>
                          <RiskBadge level={c.risk_level} />
                        </Card>
                      </Link>
                    </Reveal>
                  ))}
                </div>
              )}
            </Reveal>

            {/* Suggestions */}
            <Reveal delay={100} className="mt-8">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
                Try asking
              </h2>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <Link
                    key={s}
                    to={`/app/chat?q=${encodeURIComponent(s)}`}
                    className="lift rounded-xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 px-4 py-2.5 text-sm text-ink-600 dark:text-ink-300 shadow-soft hover:border-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
                  >
                    "{s}"
                  </Link>
                ))}
              </div>
            </Reveal>
          </div>

          {/* ── Side column ─────────────────────── */}
          <div className="space-y-6">
            <Reveal delay={80}>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
                Quick actions
              </h2>
              <div className="space-y-2.5">
                {QUICK_ACTIONS.map((a) => (
                  <Link key={a.label} to={a.to}>
                    <Card className="lift flex items-center gap-3 p-3.5">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink-100 dark:bg-ink-800 text-ink-600 dark:text-ink-300">
                        <a.icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-ink-800 dark:text-ink-100">{a.label}</p>
                        <p className="truncate text-[11px] text-ink-500 dark:text-ink-400">{a.desc}</p>
                      </div>
                    </Card>
                  </Link>
                ))}
              </div>
            </Reveal>

            {stats && stats.top_concerns.length > 0 && (
              <Reveal delay={140}>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
                  Your most discussed
                </h2>
                <Card className="p-4">
                  <ul className="space-y-2.5">
                    {stats.top_concerns.map((c) => (
                      <li key={c.name} className="flex items-center justify-between gap-3">
                        <span className="truncate text-sm capitalize text-ink-700 dark:text-ink-200">{c.name}</span>
                        <span className="shrink-0 rounded-full bg-ink-100 dark:bg-ink-800 px-2 py-0.5 text-[11px] font-semibold text-ink-500 dark:text-ink-400">
                          {c.count}×
                        </span>
                      </li>
                    ))}
                  </ul>
                </Card>
              </Reveal>
            )}

            <Reveal delay={180}>
              <Card className="relative overflow-hidden border-amber-200/70 bg-amber-50/60 p-4 dark:border-amber-900/60 dark:bg-amber-950/30">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-600 dark:bg-amber-900/60 dark:text-amber-400">
                    <Lightbulb className="h-3.5 w-3.5" />
                  </div>
                  <p className="text-sm font-semibold text-ink-800 dark:text-ink-100">Wellness tip</p>
                </div>
                <p className="text-xs leading-relaxed text-ink-600 dark:text-ink-400">{tipOfTheDay()}</p>
                <p className="mt-2 text-[10px] font-medium uppercase tracking-wide text-amber-600/80 dark:text-amber-400/70">
                  General reminder, not personalized advice
                </p>
              </Card>
            </Reveal>

            <Reveal delay={220}>
              <Card className="border-brand-200/70 dark:border-brand-900 bg-brand-50/50 dark:bg-brand-950/30 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  <p className="text-sm font-semibold text-ink-800 dark:text-ink-100">Grounded by design</p>
                </div>
                <p className="text-xs leading-relaxed text-ink-600 dark:text-ink-400">
                  Every medical claim is checked against its source before you see it. If Dr Doom
                  can't back something up, it removes it — and tells you when it doesn't know.
                </p>
              </Card>
            </Reveal>

            {(sttSupported || ttsSupported) && (
              <Reveal delay={260}>
                <Card className="p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <Mic className="h-4 w-4 text-ink-500 dark:text-ink-400" />
                    <p className="text-sm font-semibold text-ink-800 dark:text-ink-100">Voice ready</p>
                  </div>
                  <p className="text-xs leading-relaxed text-ink-600 dark:text-ink-400">
                    Your browser supports {sttSupported && ttsSupported ? "speaking and listening" : sttSupported ? "voice input" : "read-aloud"} —
                    tap the mic in any consultation to try it.
                  </p>
                </Card>
              </Reveal>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
