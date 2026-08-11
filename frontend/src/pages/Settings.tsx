import { useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  Moon,
  Sun,
  Trash2,
  Download,
  Globe,
  Volume2,
  Mic,
  ShieldCheck,
  Stethoscope,
  Mail,
  CalendarDays,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { Reveal } from "@/components/common/Reveal";
import { useThemeStore } from "@/stores/themeStore";
import { useAuthStore } from "@/stores/authStore";
import { useVoice } from "@/hooks/useVoice";
import { profileApi } from "@/services/profile";
import { conversationsApi } from "@/services/conversations";

function memberSince(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function initials(name: string | null, email: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    return (parts[0]?.[0] ?? "").concat(parts[1]?.[0] ?? "").toUpperCase() || email[0]?.toUpperCase() || "?";
  }
  return email[0]?.toUpperCase() || "?";
}

function CapabilityRow({ label, supported }: { label: string; supported: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-ink-50 px-3 py-2 dark:bg-ink-800/60">
      <span className="text-xs text-ink-600 dark:text-ink-300">{label}</span>
      {supported ? (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" /> Supported
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ink-400">
          <XCircle className="h-3.5 w-3.5" /> Not available in this browser
        </span>
      )}
    </div>
  );
}

export function Settings() {
  const { theme, set } = useThemeStore();
  const { user, deleteAccount } = useAuthStore();
  const { sttSupported, ttsSupported } = useVoice();
  const navigate = useNavigate();
  const [speechRate, setSpeechRate] = useState(1);
  const [language, setLanguage] = useState("en");
  const [exporting, setExporting] = useState(false);

  async function exportData() {
    setExporting(true);
    try {
      const [profile, conversations] = await Promise.all([profileApi.get(), conversationsApi.list()]);
      const blob = new Blob([JSON.stringify({ profile, conversations }, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "dr-doom-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  async function handleDeleteAccount() {
    if (!confirm("Permanently delete your account and all associated data? This cannot be undone.")) return;
    await deleteAccount();
    navigate("/");
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin pb-24 md:pb-0">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <Reveal>
          <h1 className="mb-1 text-2xl font-bold text-ink-900 dark:text-white">Settings</h1>
          <p className="mb-8 text-sm text-ink-500 dark:text-ink-400">
            Manage your account, appearance, and how Dr Doom talks to you.
          </p>
        </Reveal>

        {user && (
          <Reveal delay={20}>
            <Card className="mb-5 flex items-center gap-4 overflow-hidden p-6">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-bold text-white shadow-soft">
                {initials(user.full_name, user.email)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink-900 dark:text-white">
                  {user.full_name || "Your account"}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-500 dark:text-ink-400">
                  <span className="inline-flex items-center gap-1">
                    <Mail className="h-3 w-3" /> {user.email}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <CalendarDays className="h-3 w-3" /> Member since {memberSince(user.created_at)}
                  </span>
                </div>
              </div>
              {user.is_admin && (
                <span className="shrink-0 rounded-full bg-brand-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                  Admin
                </span>
              )}
            </Card>
          </Reveal>
        )}

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Reveal delay={60}>
            <Card className="h-full p-6">
              <h2 className="mb-4 text-sm font-semibold text-ink-800 dark:text-ink-100">Appearance</h2>
              <div className="flex items-center justify-between">
                <span className="text-sm text-ink-600 dark:text-ink-300">Theme</span>
                <div className="inline-flex rounded-xl border border-ink-200 bg-ink-50 p-1 dark:border-ink-700 dark:bg-ink-800">
                  <button
                    type="button"
                    onClick={() => set("light")}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                      theme === "light"
                        ? "bg-white text-ink-900 shadow-soft dark:bg-ink-900 dark:text-white"
                        : "text-ink-500 hover:text-ink-700 dark:text-ink-400 dark:hover:text-ink-200"
                    }`}
                  >
                    <Sun className="h-3.5 w-3.5" /> Light
                  </button>
                  <button
                    type="button"
                    onClick={() => set("dark")}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                      theme === "dark"
                        ? "bg-white text-ink-900 shadow-soft dark:bg-ink-900 dark:text-white"
                        : "text-ink-500 hover:text-ink-700 dark:text-ink-400 dark:hover:text-ink-200"
                    }`}
                  >
                    <Moon className="h-3.5 w-3.5" /> Dark
                  </button>
                </div>
              </div>
            </Card>
          </Reveal>

          <Reveal delay={100}>
            <Card className="h-full p-6">
              <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-800 dark:text-ink-100">
                <Globe className="h-4 w-4" /> Language
              </h2>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="input">
                <option value="en">English</option>
                <option value="hi">हिन्दी (Hindi) — coming soon</option>
                <option value="ta">தமிழ் (Tamil) — coming soon</option>
              </select>
              <p className="mt-2 text-[11px] text-ink-500 dark:text-ink-400">
                The interface and clinical knowledge base currently run in English only. Hindi and Tamil are
                planned — see README for status.
              </p>
            </Card>
          </Reveal>
        </div>

        <Reveal delay={140} className="mt-5">
          <Card className="space-y-4 p-6">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-ink-800 dark:text-ink-100">
              <Volume2 className="h-4 w-4" /> Voice
            </h2>
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-600 dark:text-ink-300">
                  Speech speed: {speechRate.toFixed(1)}×
                </label>
                <input
                  type="range"
                  min={0.5}
                  max={1.5}
                  step={0.1}
                  value={speechRate}
                  onChange={(e) => setSpeechRate(Number(e.target.value))}
                  className="w-full accent-brand-600"
                />
                {(!sttSupported || !ttsSupported) && (
                  <p className="mt-3 flex items-start gap-1.5 text-[11px] text-ink-500 dark:text-ink-400">
                    <Mic className="mt-0.5 h-3 w-3 shrink-0" />
                    Voice runs entirely in your browser (no server round-trip) — try Chrome or Edge for
                    full support.
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <CapabilityRow label="Speech-to-text (microphone input)" supported={sttSupported} />
                <CapabilityRow label="Text-to-speech (Listen button)" supported={ttsSupported} />
              </div>
            </div>
          </Card>
        </Reveal>

        <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Reveal delay={180}>
            <Card className="h-full p-6">
              <h2 className="mb-2 text-sm font-semibold text-ink-800 dark:text-ink-100">Privacy & data retention</h2>
              <p className="mb-4 text-xs text-ink-500 dark:text-ink-400">
                Your conversations and health profile are stored in the application database until you
                delete them. Deleting a conversation or your account removes it permanently.
              </p>
              <Button size="sm" variant="outline" className="gap-1.5" onClick={exportData} disabled={exporting}>
                <Download className="h-3.5 w-3.5" /> {exporting ? "Preparing…" : "Export my data"}
              </Button>
            </Card>
          </Reveal>

          <Reveal delay={220}>
            <Card className="h-full p-6">
              <h2 className="mb-2 text-sm font-semibold text-red-600 dark:text-red-400">Danger zone</h2>
              <p className="mb-4 text-xs text-ink-500 dark:text-ink-400">
                Permanently delete your account, health profile, and all consultations.
              </p>
              <Button variant="danger" size="sm" className="gap-1.5" onClick={handleDeleteAccount}>
                <Trash2 className="h-3.5 w-3.5" /> Delete account
              </Button>
            </Card>
          </Reveal>
        </div>

        <Reveal delay={260} className="mt-5">
          <Card className="flex items-start gap-3 border-brand-200/70 bg-brand-50/50 p-4 dark:border-brand-900 dark:bg-brand-950/30">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
              <Stethoscope className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-ink-800 dark:text-ink-100">
                Dr Doom <ShieldCheck className="h-3.5 w-3.5 text-brand-500" />
              </p>
              <p className="mt-1 text-xs leading-relaxed text-ink-600 dark:text-ink-400">
                Evidence-grounded health intelligence, sourced from MedlinePlus (U.S. National Library of
                Medicine / NIH). Every factual claim is checked against a cited source before it reaches
                you — see the Assessment panel on any consultation for details.
              </p>
            </div>
          </Card>
        </Reveal>
      </div>
    </div>
  );
}
