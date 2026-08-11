import { ReactNode, useEffect, useState } from "react";
import { Trash2, Save } from "lucide-react";
import { Card } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { profileApi } from "@/services/profile";
import type { HealthProfile } from "@/types/api";

const EMPTY: HealthProfile = {
  id: "",
  age: null,
  sex: null,
  height_cm: null,
  weight_kg: null,
  allergies: [],
  known_conditions: [],
  medications: [],
  medical_history: [],
  pregnancy_status: null,
  lifestyle: {},
  emergency_contact: null,
};

function listToText(list: string[]) {
  return (list || []).join(", ");
}
function textToList(text: string) {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function Profile() {
  const [profile, setProfile] = useState<HealthProfile>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    profileApi.get().then((p) => {
      setProfile(p);
      setLoading(false);
    });
  }, []);

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await profileApi.update(profile);
      setProfile(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  async function deleteAll() {
    if (!confirm("Delete all of your health profile data? This cannot be undone.")) return;
    await profileApi.remove();
    setProfile(EMPTY);
  }

  if (loading) return <div className="flex-1 p-10 text-sm text-ink-400">Loading…</div>;

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="mb-1 text-2xl font-bold text-ink-900 dark:text-white">Health profile</h1>
        <p className="mb-8 text-sm text-ink-500 dark:text-ink-400">
          Everything here is optional. It helps Dr Doom skip questions it already knows the answer to.
        </p>

        <Card className="mb-5 space-y-4 p-6">
          <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Personal information</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Age">
              <input
                type="number"
                value={profile.age ?? ""}
                onChange={(e) => setProfile({ ...profile, age: e.target.value ? Number(e.target.value) : null })}
                className="input"
              />
            </Field>
            <Field label="Sex">
              <select
                value={profile.sex ?? ""}
                onChange={(e) => setProfile({ ...profile, sex: e.target.value || null })}
                className="input"
              >
                <option value="">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="intersex">Intersex</option>
              </select>
            </Field>
            <Field label="Height (cm)">
              <input
                type="number"
                value={profile.height_cm ?? ""}
                onChange={(e) => setProfile({ ...profile, height_cm: e.target.value ? Number(e.target.value) : null })}
                className="input"
              />
            </Field>
            <Field label="Weight (kg)">
              <input
                type="number"
                value={profile.weight_kg ?? ""}
                onChange={(e) => setProfile({ ...profile, weight_kg: e.target.value ? Number(e.target.value) : null })}
                className="input"
              />
            </Field>
            <Field label="Pregnancy status">
              <select
                value={profile.pregnancy_status ?? ""}
                onChange={(e) => setProfile({ ...profile, pregnancy_status: e.target.value || null })}
                className="input"
              >
                <option value="">Not specified</option>
                <option value="pregnant">Pregnant</option>
                <option value="not_pregnant">Not pregnant</option>
                <option value="unknown">Not sure</option>
                <option value="na">Not applicable</option>
              </select>
            </Field>
          </div>
        </Card>

        <Card className="mb-5 space-y-4 p-6">
          <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Medical history</h2>
          <Field label="Known conditions (comma-separated)">
            <input
              value={listToText(profile.known_conditions)}
              onChange={(e) => setProfile({ ...profile, known_conditions: textToList(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Relevant medical history (comma-separated)">
            <input
              value={listToText(profile.medical_history)}
              onChange={(e) => setProfile({ ...profile, medical_history: textToList(e.target.value) })}
              className="input"
            />
          </Field>
        </Card>

        <Card className="mb-5 space-y-4 p-6">
          <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Current medications & allergies</h2>
          <Field label="Current medications (comma-separated)">
            <input
              value={listToText(profile.medications)}
              onChange={(e) => setProfile({ ...profile, medications: textToList(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Known drug allergies (comma-separated)">
            <input
              value={listToText(profile.allergies)}
              onChange={(e) => setProfile({ ...profile, allergies: textToList(e.target.value) })}
              className="input"
            />
          </Field>
        </Card>

        <div className="flex items-center justify-between">
          <Button variant="danger" className="gap-1.5" onClick={deleteAll}>
            <Trash2 className="h-4 w-4" /> Delete my health data
          </Button>
          <Button className="gap-1.5" onClick={save} disabled={saving}>
            <Save className="h-4 w-4" /> {saving ? "Saving…" : saved ? "Saved!" : "Save changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink-600 dark:text-ink-300">{label}</span>
      {children}
    </label>
  );
}
