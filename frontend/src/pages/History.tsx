import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Trash2,
  Pencil,
  Check,
  X,
  MessageSquarePlus,
  Search,
  Activity,
  History as HistoryIcon,
  Download,
  FileText,
} from "lucide-react";
import { Card } from "@/components/common/Card";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Button } from "@/components/common/Button";
import { Reveal } from "@/components/common/Reveal";
import { conversationsApi } from "@/services/conversations";
import { summariesApi } from "@/services/summaries";
import { API_URL } from "@/services/api";
import type { ConversationCard, ConsultationSummary } from "@/types/api";

type Filter = "all" | "complete" | "in_progress" | "urgent";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "complete", label: "Completed" },
  { key: "in_progress", label: "In progress" },
  { key: "urgent", label: "Urgent" },
];

/** Buckets a date into a human-readable section header. */
function bucketOf(iso: string): string {
  const then = new Date(iso);
  const days = Math.floor((Date.now() - then.getTime()) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return "This week";
  if (days < 30) return "This month";
  return "Earlier";
}

const BUCKET_ORDER = ["Today", "Yesterday", "This week", "This month", "Earlier"];

export function HistoryPage() {
  const [items, setItems] = useState<ConversationCard[]>([]);
  const [summaries, setSummaries] = useState<ConsultationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  function load() {
    setLoading(true);
    Promise.all([conversationsApi.list(), summariesApi.list().catch(() => [])])
      .then(([rows, sums]) => {
        setItems(rows);
        setSummaries(sums as ConsultationSummary[]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  // conversation_id -> summary id, so a row can offer a direct PDF download.
  const summaryByConversation = useMemo(() => {
    const map: Record<string, string> = {};
    for (const s of summaries) {
      if (s.conversation_id && s.id) map[s.conversation_id] = s.id;
    }
    return map;
  }, [summaries]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((c) => {
      if (filter === "complete" && !c.is_complete) return false;
      if (filter === "in_progress" && c.is_complete) return false;
      if (filter === "urgent" && !["urgent", "emergency"].includes(c.risk_level)) return false;
      if (!q) return true;
      return (
        c.title.toLowerCase().includes(q) ||
        (c.primary_complaint || "").toLowerCase().includes(q)
      );
    });
  }, [items, query, filter]);

  const grouped = useMemo(() => {
    const groups: Record<string, ConversationCard[]> = {};
    for (const c of filtered) {
      const bucket = bucketOf(c.updated_at);
      (groups[bucket] ||= []).push(c);
    }
    return BUCKET_ORDER.filter((b) => groups[b]?.length).map((b) => ({ bucket: b, rows: groups[b] }));
  }, [filtered]);

  async function remove(id: string) {
    if (!confirm("Delete this consultation permanently? This cannot be undone.")) return;
    await conversationsApi.remove(id);
    setItems((prev) => prev.filter((c) => c.id !== id));
  }

  async function saveRename(id: string) {
    const updated = await conversationsApi.rename(id, draftTitle);
    setItems((prev) => prev.map((c) => (c.id === id ? updated : c)));
    setEditingId(null);
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin pb-24 md:pb-0">
      <div className="mx-auto max-w-4xl px-6 py-10">
        {/* Header */}
        <div className="animate-fade-up mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-ink-900 dark:text-white">
              Consultation history
            </h1>
            <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">
              {items.length} consultation{items.length === 1 ? "" : "s"} saved
            </p>
          </div>
          <Link to="/app/chat">
            <Button size="sm" className="gap-1.5">
              <MessageSquarePlus className="h-4 w-4" /> New consultation
            </Button>
          </Link>
        </div>

        {/* Search + filters */}
        <div className="animate-fade-up mb-6 space-y-3 [animation-delay:80ms]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search consultations…"
              className="w-full rounded-xl border border-ink-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none transition-shadow focus:ring-2 focus:ring-brand-400 dark:border-ink-700 dark:bg-ink-900"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  filter === f.key
                    ? "bg-brand-600 text-white"
                    : "border border-ink-200 bg-white text-ink-600 hover:border-brand-400 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-300"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-[74px] animate-pulse rounded-2xl bg-ink-100 dark:bg-ink-800" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Card className="flex flex-col items-center gap-3 p-14 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-ink-100 dark:bg-ink-800">
              <HistoryIcon className="h-6 w-6 text-ink-400" />
            </div>
            <div>
              <p className="font-medium text-ink-700 dark:text-ink-200">
                {items.length === 0 ? "No consultations yet" : "No matches"}
              </p>
              <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">
                {items.length === 0
                  ? "Your consultations will be saved here automatically."
                  : "Try a different search term or filter."}
              </p>
            </div>
            {items.length === 0 && (
              <Link to="/app/chat" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-400">
                Start your first consultation →
              </Link>
            )}
          </Card>
        ) : (
          <div className="space-y-8">
            {grouped.map(({ bucket, rows }) => (
              <div key={bucket}>
                <h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-ink-400">{bucket}</h2>
                <div className="space-y-3">
                  {rows.map((c, i) => {
                    const summaryId = summaryByConversation[c.id];
                    return (
                      <Reveal key={c.id} delay={i * 50}>
                        <Card className="lift flex items-center gap-3 p-4">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-950 dark:text-brand-400">
                            <Activity className="h-4 w-4" />
                          </div>

                          <div className="min-w-0 flex-1">
                            {editingId === c.id ? (
                              <div className="flex items-center gap-2">
                                <input
                                  value={draftTitle}
                                  onChange={(e) => setDraftTitle(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter") saveRename(c.id);
                                    if (e.key === "Escape") setEditingId(null);
                                  }}
                                  className="w-full rounded-lg border border-ink-200 bg-transparent px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-brand-400 dark:border-ink-700"
                                  autoFocus
                                />
                                <button type="button" onClick={() => saveRename(c.id)} className="text-brand-600">
                                  <Check className="h-4 w-4" />
                                </button>
                                <button type="button" onClick={() => setEditingId(null)} className="text-ink-400">
                                  <X className="h-4 w-4" />
                                </button>
                              </div>
                            ) : (
                              <Link to={`/app/chat/${c.id}`} className="block">
                                <p className="truncate text-sm font-semibold text-ink-800 dark:text-ink-100">
                                  {c.title}
                                </p>
                                <p className="mt-0.5 text-xs text-ink-500 dark:text-ink-400">
                                  {new Date(c.updated_at).toLocaleDateString(undefined, {
                                    month: "short",
                                    day: "numeric",
                                    year: "numeric",
                                  })}
                                  {c.primary_complaint ? ` · ${c.primary_complaint}` : ""}
                                  {c.is_complete ? "" : " · in progress"}
                                </p>
                              </Link>
                            )}
                          </div>

                          <RiskBadge level={c.risk_level} />

                          <div className="flex shrink-0 items-center gap-0.5">
                            {summaryId && (
                              <a
                                href={`${API_URL}/api/summaries/${summaryId}/pdf`}
                                target="_blank"
                                rel="noreferrer"
                                title="Download PDF summary"
                                className="rounded-lg p-2 text-ink-400 transition-colors hover:bg-ink-100 hover:text-brand-600 dark:hover:bg-ink-800"
                              >
                                <Download className="h-4 w-4" />
                              </a>
                            )}
                            <button
                              type="button"
                              title="Rename"
                              onClick={() => {
                                setEditingId(c.id);
                                setDraftTitle(c.title);
                              }}
                              className="rounded-lg p-2 text-ink-400 transition-colors hover:bg-ink-100 dark:hover:bg-ink-800"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              title="Delete"
                              onClick={() => remove(c.id)}
                              className="rounded-lg p-2 text-red-500 transition-colors hover:bg-red-50 dark:hover:bg-red-950/40"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </Card>
                      </Reveal>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Saved summaries */}
        {!loading && summaries.length > 0 && (
          <Reveal className="mt-12">
            <h2 className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-ink-400">
              <FileText className="h-3.5 w-3.5" /> Saved summaries ({summaries.length})
            </h2>
            <Card className="divide-y divide-ink-100 dark:divide-ink-800">
              {summaries.map((s) => (
                <div key={s.id} className="flex items-center gap-3 p-4">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink-800 dark:text-ink-100">
                      {s.conversation_title || s.primary_concern || "Consultation summary"}
                    </p>
                    <p className="text-xs text-ink-500 dark:text-ink-400">
                      {s.created_at
                        ? new Date(s.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                        : ""}
                      {s.symptoms?.length ? ` · ${s.symptoms.join(", ")}` : ""}
                    </p>
                  </div>
                  <RiskBadge level={s.risk_level} />
                  <a
                    href={`${API_URL}/api/summaries/${s.id}/pdf`}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-lg p-2 text-ink-400 transition-colors hover:bg-ink-100 hover:text-brand-600 dark:hover:bg-ink-800"
                    title="Download PDF"
                  >
                    <Download className="h-4 w-4" />
                  </a>
                </div>
              ))}
            </Card>
          </Reveal>
        )}
      </div>
    </div>
  );
}
