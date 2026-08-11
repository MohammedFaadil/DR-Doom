import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Moon, Sun, Trash2, Download, Globe, Volume2 } from "lucide-react";
import { Card } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { useThemeStore } from "@/stores/themeStore";
import { useAuthStore } from "@/stores/authStore";
import { profileApi } from "@/services/profile";
import { conversationsApi } from "@/services/conversations";

export function Settings() {
  const { theme, set } = useThemeStore();
  const { deleteAccount } = useAuthStore();
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
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="mb-8 text-2xl font-bold text-ink-900 dark:text-white">Settings</h1>

        <Card className="mb-5 p-6">
          <h2 className="mb-4 text-sm font-semibold text-ink-800 dark:text-ink-100">Appearance</h2>
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-600 dark:text-ink-300">Theme</span>
            <div className="flex gap-2">
              <Button size="sm" variant={theme === "light" ? "primary" : "outline"} className="gap-1.5" onClick={() => set("light")}>
                <Sun className="h-3.5 w-3.5" /> Light
              </Button>
              <Button size="sm" variant={theme === "dark" ? "primary" : "outline"} className="gap-1.5" onClick={() => set("dark")}>
                <Moon className="h-3.5 w-3.5" /> Dark
              </Button>
            </div>
          </div>
        </Card>

        <Card className="mb-5 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-800 dark:text-ink-100">
            <Globe className="h-4 w-4" /> Language
          </h2>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="input">
            <option value="en">English</option>
            <option value="hi">हिन्दी (Hindi) — coming soon</option>
            <option value="ta">தமிழ் (Tamil) — coming soon</option>
          </select>
          <p className="mt-2 text-[11px] text-ink-500 dark:text-ink-400">
            The interface and clinical knowledge base currently run in English only. Hindi and Tamil are planned —
            see README for status.
          </p>
        </Card>

        <Card className="mb-5 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink-800 dark:text-ink-100">
            <Volume2 className="h-4 w-4" /> Voice
          </h2>
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
        </Card>

        <Card className="mb-5 p-6">
          <h2 className="mb-2 text-sm font-semibold text-ink-800 dark:text-ink-100">Privacy & data retention</h2>
          <p className="mb-4 text-xs text-ink-500 dark:text-ink-400">
            Your conversations and health profile are stored in the application database until you delete them.
            Deleting a conversation or your account removes it permanently.
          </p>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={exportData} disabled={exporting}>
            <Download className="h-3.5 w-3.5" /> {exporting ? "Preparing…" : "Export my data"}
          </Button>
        </Card>

        <Card className="p-6">
          <h2 className="mb-2 text-sm font-semibold text-red-600 dark:text-red-400">Danger zone</h2>
          <p className="mb-4 text-xs text-ink-500 dark:text-ink-400">
            Permanently delete your account, health profile, and all consultations.
          </p>
          <Button variant="danger" size="sm" className="gap-1.5" onClick={handleDeleteAccount}>
            <Trash2 className="h-3.5 w-3.5" /> Delete account
          </Button>
        </Card>
      </div>
    </div>
  );
}
