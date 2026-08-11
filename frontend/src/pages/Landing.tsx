import { Link } from "react-router-dom";
import {
  Stethoscope,
  Mic,
  MessageSquareText,
  Search,
  ShieldCheck,
  BookOpenCheck,
  ArrowRight,
  Activity,
  FileText,
  Lock,
  Sparkles,
  AlertTriangle,
  ListChecks,
  Quote,
  Database,
  Github,
} from "lucide-react";
import { Button } from "@/components/common/Button";
import { Disclaimer } from "@/components/common/Disclaimer";
import { Reveal } from "@/components/common/Reveal";

const STEPS = [
  {
    title: "Tell us what you're experiencing",
    desc: "Describe symptoms in your own words, or use your voice. No forms, no jargon.",
    icon: MessageSquareText,
  },
  {
    title: "Dr Doom asks the right questions",
    desc: "Focused clinical follow-ups, one at a time — and it stops as soon as it has enough.",
    icon: ListChecks,
  },
  {
    title: "Verified medical knowledge is retrieved",
    desc: "Hybrid semantic + keyword search across a curated NIH/MedlinePlus corpus.",
    icon: BookOpenCheck,
  },
  {
    title: "Your symptoms are assessed",
    desc: "Structured interpretation of evidence against your profile — never a guess.",
    icon: Search,
  },
  {
    title: "You get a grounded explanation",
    desc: "Every claim checked against its source. Unsupported statements are removed.",
    icon: ShieldCheck,
  },
  {
    title: "Your summary is saved",
    desc: "Revisit it, continue the conversation, or export a clean PDF for your doctor.",
    icon: FileText,
  },
];

const PILLARS = [
  {
    icon: AlertTriangle,
    title: "Emergency screening first",
    body: "Every single message is checked against deterministic red-flag rules — chest pain with radiation, stroke signs, anaphylaxis — before anything else runs. That check is plain code, never left to a language model's judgment.",
    accent: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50",
  },
  {
    icon: BookOpenCheck,
    title: "Grounded in real sources",
    body: "Answers are composed from documents fetched from the U.S. National Library of Medicine. Every citation is a real, clickable page — there are no invented studies, statistics, or guidelines.",
    accent: "text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-950/50",
  },
  {
    icon: ShieldCheck,
    title: "It says when it doesn't know",
    body: "If retrieval finds nothing relevant, Dr Doom tells you so instead of improvising. A grounding validator strips any sentence it can't trace back to the evidence.",
    accent: "text-indigo-600 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/50",
  },
  {
    icon: Lock,
    title: "Your data stays yours",
    body: "Health content is never written to application logs. Delete a consultation, wipe your health profile, export everything as JSON, or remove your account entirely — at any time.",
    accent: "text-amber-600 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/50",
  },
];

const STATS = [
  { value: "544", label: "Evidence passages indexed" },
  { value: "74", label: "Curated source documents" },
  { value: "12", label: "Red-flag emergency rules" },
  { value: "100%", label: "Answers with citations" },
];

const COVERAGE = [
  "Fever", "Headache & migraine", "Cough & cold", "Sore throat", "Chest pain",
  "Breathing problems", "Stomach & digestive", "Back & joint pain", "Skin & rashes",
  "Sleep & stress", "Women's health", "Men's health", "Pediatrics", "Elderly care",
  "Common medications",
];

export function Landing() {
  return (
    <div className="min-h-screen bg-white dark:bg-ink-950">
      {/* ── Nav ───────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-ink-200/60 dark:border-ink-800/60 bg-white/80 dark:bg-ink-950/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-soft">
              <Stethoscope className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <p className="text-base font-extrabold tracking-tight">DR DOOM</p>
              <p className="text-[10px] text-ink-500 dark:text-ink-400">Evidence-grounded AI</p>
            </div>
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            <nav className="hidden items-center gap-1 sm:flex">
              <a
                href="#how-it-works"
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900 dark:text-ink-300 dark:hover:bg-ink-800 dark:hover:text-white"
              >
                How it works
              </a>
              <a
                href="#safety"
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900 dark:text-ink-300 dark:hover:bg-ink-800 dark:hover:text-white"
              >
                Safety
              </a>
            </nav>
            <div className="mx-1 hidden h-5 w-px bg-ink-200 dark:bg-ink-800 sm:block" />
            <Link
              to="/login"
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900 dark:text-ink-300 dark:hover:bg-ink-800 dark:hover:text-white"
            >
              Sign in
            </Link>
            <Link to="/register" className="ml-1">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* ── Hero ───────────────────────────────────────────── */}
        <section className="relative overflow-hidden aurora">
          <div className="pointer-events-none absolute -left-24 top-20 h-64 w-64 rounded-full bg-brand-300/20 blur-3xl animate-float" />
          <div className="pointer-events-none absolute -right-24 top-40 h-72 w-72 rounded-full bg-brand-500/10 blur-3xl animate-float [animation-delay:1.5s]" />

          <div className="relative mx-auto max-w-6xl px-6 py-20 text-center md:py-28">
            <div className="mx-auto mb-6 inline-flex animate-fade-in-slow items-center gap-2 rounded-full border border-brand-200 dark:border-brand-800 bg-white/70 dark:bg-brand-950/40 px-4 py-1.5 text-xs font-medium text-brand-700 dark:text-brand-300 backdrop-blur">
              <Sparkles className="h-3.5 w-3.5" />
              Evidence-grounded · Real NIH sources · Free to use
            </div>

            <h1 className="animate-fade-up text-4xl font-extrabold leading-[1.1] tracking-tight text-ink-900 dark:text-white sm:text-6xl md:text-7xl">
              Meet <span className="text-gradient-brand animate-gradient-pan">Dr Doom</span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl animate-fade-up text-lg leading-relaxed text-ink-600 dark:text-ink-300 [animation-delay:120ms] sm:text-xl">
              An evidence-grounded AI health companion that thinks through your symptoms
              systematically — asking the right clinical questions, citing real medical sources,
              and telling you plainly when it doesn't know.
            </p>

            <div className="mt-9 flex animate-fade-up flex-col items-center justify-center gap-3 [animation-delay:240ms] sm:flex-row">
              <Link to="/register">
                <Button size="lg" className="group gap-2 shadow-lg shadow-brand-600/20">
                  Start Health Assessment
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Button>
              </Link>
              <a href="#how-it-works">
                <Button size="lg" variant="outline">Explore How It Works</Button>
              </a>
            </div>

            <div className="mt-6 flex animate-fade-up flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-ink-500 dark:text-ink-400 [animation-delay:340ms]">
              <span className="inline-flex items-center gap-1.5"><Mic className="h-3.5 w-3.5" /> Voice input</span>
              <span className="inline-flex items-center gap-1.5"><FileText className="h-3.5 w-3.5" /> PDF summaries</span>
              <span className="inline-flex items-center gap-1.5"><Lock className="h-3.5 w-3.5" /> Private by design</span>
            </div>

            {/* Faux conversation preview */}
            <Reveal delay={200} className="mx-auto mt-16 max-w-2xl">
              <div className="rounded-3xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-5 text-left shadow-2xl shadow-ink-900/5">
                <div className="mb-4 flex items-center gap-2 border-b border-ink-100 dark:border-ink-800 pb-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                  <span className="h-2.5 w-2.5 rounded-full bg-brand-400" />
                  <span className="ml-2 text-xs font-medium text-ink-400">Consultation</span>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-end">
                    <p className="rounded-2xl rounded-tr-md bg-brand-600 px-3.5 py-2 text-sm text-white">
                      I've had a headache since this morning
                    </p>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
                      <Stethoscope className="h-3.5 w-3.5" />
                    </div>
                    <div className="rounded-2xl rounded-tl-md border border-ink-200/70 dark:border-ink-800 bg-ink-50 dark:bg-ink-800/60 px-3.5 py-2.5">
                      <p className="text-sm text-ink-700 dark:text-ink-200">
                        Are you experiencing any of these along with the headache?
                      </p>
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {["Vision changes", "Neck stiffness", "Weakness on one side", "None of these"].map((o) => (
                          <span key={o} className="rounded-lg border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-2.5 py-1 text-xs font-medium text-ink-600 dark:text-ink-300">
                            {o}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ── Stats ───────────────────────────────────────────── */}
        <section className="border-y border-ink-200/60 dark:border-ink-800/60 bg-ink-50/60 dark:bg-ink-900/40">
          <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-6 py-10 md:grid-cols-4">
            {STATS.map((s, i) => (
              <Reveal key={s.label} delay={i * 90} className="text-center">
                <p className="text-3xl font-extrabold text-gradient-brand sm:text-4xl">{s.value}</p>
                <p className="mt-1 text-xs font-medium text-ink-500 dark:text-ink-400">{s.label}</p>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ── How it works ───────────────────────────────────── */}
        <section id="how-it-works" className="scroll-mt-24 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <Reveal className="mx-auto max-w-2xl text-center">
              <p className="mb-2 text-xs font-bold uppercase tracking-widest text-brand-600 dark:text-brand-400">
                The process
              </p>
              <h2 className="text-3xl font-bold tracking-tight text-ink-900 dark:text-white sm:text-4xl">
                How Dr Doom works
              </h2>
              <p className="mt-4 text-ink-600 dark:text-ink-400">
                Six deliberate steps — the intelligence comes from structure and evidence, not from
                handing a language model a giant prompt.
              </p>
            </Reveal>

            <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {STEPS.map((step, i) => (
                <Reveal key={step.title} delay={i * 80}>
                  <div className="lift group h-full rounded-2xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-6 shadow-soft">
                    <div className="mb-4 flex items-center justify-between">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-100 dark:bg-brand-950 text-brand-700 dark:text-brand-300 transition-transform duration-300 group-hover:scale-110">
                        <step.icon className="h-5 w-5" />
                      </div>
                      <span className="text-3xl font-extrabold text-ink-100 dark:text-ink-800">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                    </div>
                    <h3 className="mb-1.5 font-semibold text-ink-900 dark:text-white">{step.title}</h3>
                    <p className="text-sm leading-relaxed text-ink-600 dark:text-ink-400">{step.desc}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ── Safety pillars ─────────────────────────────────── */}
        <section id="safety" className="scroll-mt-24 border-y border-ink-200/60 dark:border-ink-800/60 bg-ink-50/60 dark:bg-ink-900/40 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <Reveal className="mx-auto max-w-2xl text-center">
              <p className="mb-2 text-xs font-bold uppercase tracking-widest text-brand-600 dark:text-brand-400">
                Built for safety
              </p>
              <h2 className="text-3xl font-bold tracking-tight text-ink-900 dark:text-white sm:text-4xl">
                Why you can trust what it says
              </h2>
              <p className="mt-4 text-ink-600 dark:text-ink-400">
                Health information is only useful if it's honest about its limits. These are the
                guarantees built into the system itself.
              </p>
            </Reveal>

            <div className="mt-14 grid grid-cols-1 gap-5 md:grid-cols-2">
              {PILLARS.map((p, i) => (
                <Reveal key={p.title} delay={i * 100}>
                  <div className="lift h-full rounded-2xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-7 shadow-soft">
                    <div className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl ${p.accent}`}>
                      <p.icon className="h-5 w-5" />
                    </div>
                    <h3 className="mb-2 text-lg font-semibold text-ink-900 dark:text-white">{p.title}</h3>
                    <p className="text-sm leading-relaxed text-ink-600 dark:text-ink-400">{p.body}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ── Coverage ───────────────────────────────────────── */}
        <section className="py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
              <Reveal>
                <p className="mb-2 text-xs font-bold uppercase tracking-widest text-brand-600 dark:text-brand-400">
                  Knowledge base
                </p>
                <h2 className="text-3xl font-bold tracking-tight text-ink-900 dark:text-white sm:text-4xl">
                  Real sources, not scraped blogs
                </h2>
                <p className="mt-4 leading-relaxed text-ink-600 dark:text-ink-400">
                  Every passage in Dr Doom's knowledge base is fetched directly from{" "}
                  <span className="font-semibold text-ink-800 dark:text-ink-200">MedlinePlus</span>, published
                  by the U.S. National Library of Medicine. Drug information is resolved through the
                  official RxNorm and MedlinePlus Connect APIs.
                </p>
                <p className="mt-3 leading-relaxed text-ink-600 dark:text-ink-400">
                  If a source can't be fetched, it's skipped and logged — never substituted with
                  content an AI made up.
                </p>
                <div className="mt-6 inline-flex items-center gap-2 rounded-xl border border-ink-200 dark:border-ink-800 bg-ink-50 dark:bg-ink-900 px-4 py-2.5">
                  <Database className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  <span className="text-sm font-medium text-ink-700 dark:text-ink-300">
                    544 passages · 74 documents · versioned
                  </span>
                </div>
              </Reveal>

              <Reveal delay={150}>
                <div className="flex flex-wrap gap-2.5">
                  {COVERAGE.map((c, i) => (
                    <span
                      key={c}
                      className="lift rounded-xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 px-4 py-2.5 text-sm font-medium text-ink-700 dark:text-ink-300 shadow-soft"
                      style={{ animationDelay: `${i * 40}ms` }}
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ── Honesty note ───────────────────────────────────── */}
        <section className="pb-20">
          <div className="mx-auto max-w-4xl px-6">
            <Reveal>
              <div className="relative overflow-hidden rounded-3xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-8 shadow-soft sm:p-10">
                <Quote className="absolute -right-4 -top-4 h-28 w-28 text-ink-50 dark:text-ink-800/60" />
                <div className="relative">
                  <p className="mb-2 text-xs font-bold uppercase tracking-widest text-brand-600 dark:text-brand-400">
                    What Dr Doom is not
                  </p>
                  <p className="text-lg leading-relaxed text-ink-700 dark:text-ink-200 sm:text-xl">
                    Dr Doom is an <span className="font-semibold">evidence-grounded clinical information and
                    triage assistant</span> — not a chatbot pretending to be a doctor. It does not diagnose,
                    does not prescribe, does not claim to be accurate 100% of the time, and will never
                    invent a medicine, a dose, a study, or a citation.
                  </p>
                  <p className="mt-4 text-sm text-ink-500 dark:text-ink-400">
                    When it lacks evidence, it says so. That's the whole point.
                  </p>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ── CTA ────────────────────────────────────────────── */}
        <section className="pb-20">
          <div className="mx-auto max-w-4xl px-6">
            <Reveal>
              <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-10 text-center shadow-2xl shadow-brand-900/20 sm:p-14">
                <div className="pointer-events-none absolute -left-16 -top-16 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
                <div className="pointer-events-none absolute -bottom-20 -right-10 h-56 w-56 rounded-full bg-brand-300/20 blur-3xl" />
                <div className="relative">
                  <Activity className="mx-auto mb-5 h-10 w-10 text-white/90" />
                  <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                    Understand your symptoms properly
                  </h2>
                  <p className="mx-auto mt-4 max-w-lg text-brand-50/90">
                    Free to use. Your first evidence-grounded consultation takes about two minutes.
                  </p>
                  <Link to="/register" className="mt-8 inline-block">
                    <Button size="lg" variant="secondary" className="group gap-2 bg-white text-brand-700 hover:bg-brand-50">
                      Start Health Assessment
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </Button>
                  </Link>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        <section className="pb-20">
          <div className="mx-auto max-w-4xl px-6">
            <Reveal>
              <Disclaimer />
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink-200/60 dark:border-ink-800/60 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 sm:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Stethoscope className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-bold tracking-tight">DR DOOM</span>
          </div>
          <p className="text-center text-xs text-ink-500 dark:text-ink-500">
            © {new Date().getFullYear()} Dr Doom — Evidence-grounded health intelligence. Educational use only.
          </p>
          <span className="inline-flex items-center gap-1.5 text-xs text-ink-400">
            <Github className="h-3.5 w-3.5" /> Open architecture
          </span>
        </div>
      </footer>
    </div>
  );
}
