import { ReactNode, useEffect, useMemo, useState } from "react";
import {
  Trash2,
  Save,
  User2,
  HeartPulse,
  Pill,
  ShieldAlert,
  Activity,
  PhoneCall,
  Sparkles,
  Check,
} from "lucide-react";
import { Card } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { Reveal } from "@/components/common/Reveal";
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

function bmiInfo(heightCm: number | null, weightKg: number | null) {
  if (!heightCm || !weightKg) return null;
  const meters = heightCm / 100;
  const bmi = weightKg / (meters * meters);
  if (!Number.isFinite(bmi) || bmi <= 0) return null;
  let label = "Normal";
  let tone = "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50";
  if (bmi < 18.5) {
    label = "Underweight";
    tone = "text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/50";
  } else if (bmi >= 25 && bmi < 30) {
    label = "Overweight";
    tone = "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50";
  } else if (bmi >= 30) {
    label = "Obese range";
    tone = "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50";
  }
  return { value: bmi.toFixed(1), label, tone };
}

function ChipPreview({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-medium capitalize text-brand-700 dark:bg-brand-950/60 dark:text-brand-300"
        >
          {item}
        </span>
      ))}
    </div>
  );
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
      setTimeout(() => setSaved(false), 2200);
    } finally {
      setSaving(false);
    }
  }

  async function deleteAll() {
    if (!confirm("Delete all of your health profile data? This cannot be undone.")) return;
    await profileApi.remove();
    setProfile(EMPTY);
  }

  const lifestyle = (profile.lifestyle || {}) as Record<string, string>;
  const emergencyContact = (profile.emergency_contact || {}) as Record<string, string>;

  function setLifestyle(key: string, value: string) {
    setProfile({ ...profile, lifestyle: { ...lifestyle, [key]: value } });
  }
  function setEmergencyContact(key: string, value: string) {
    setProfile({ ...profile, emergency_contact: { ...emergencyContact, [key]: value } });
  }

  const bmi = useMemo(() => bmiInfo(profile.height_cm, profile.weight_kg), [profile.height_cm, profile.weight_kg]);

  const completeness = useMemo(() => {
    const checks = [
      !!profile.age,
      !!profile.sex,
      !!profile.height_cm,
      !!profile.weight_kg,
      profile.known_conditions.length > 0,
      profile.medical_history.length > 0,
      profile.medications.length > 0,
      profile.allergies.length > 0,
      Object.values(lifestyle).some(Boolean),
      !!emergencyContact.name && !!emergencyContact.phone,
    ];
    const done = checks.filter(Boolean).length;
    return Math.round((done / checks.length) * 100);
  }, [profile, lifestyle, emergencyContact]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <User2 className="h-6 w-6 animate-pulse text-brand-500" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin pb-24 md:pb-0">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <Reveal>
          <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Health profile</h1>
              <p className="mt-1 text-sm text-ink-500 dark:text-ink-400">
                Everything here is optional. It helps Dr Doom skip questions it already knows the answer
                to and tailor guidance to you specifically.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3 rounded-2xl border border-ink-200/70 bg-white p-3 shadow-soft dark:border-ink-800 dark:bg-ink-900">
              <div className="relative h-14 w-14 shrink-0">
                <svg viewBox="0 0 40 40" className="h-14 w-14 -rotate-90">
                  <circle cx="20" cy="20" r="16" fill="none" strokeWidth="4" className="stroke-ink-100 dark:stroke-ink-800" />
                  <circle
                    cx="20"
                    cy="20"
                    r="16"
                    fill="none"
                    strokeWidth="4"
                    strokeLinecap="round"
                    className="stroke-brand-500 transition-all duration-700"
                    strokeDasharray={2 * Math.PI * 16}
                    strokeDashoffset={2 * Math.PI * 16 * (1 - completeness / 100)}
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-ink-800 dark:text-ink-100">
                  {completeness}%
                </span>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-500 dark:text-ink-400">
                  Profile strength
                </p>
                <p className="text-xs text-ink-400 dark:text-ink-500">
                  {completeness < 100 ? "Fill more sections for sharper guidance" : "Fully complete — nice!"}
                </p>
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal delay={40}>
          <Card className="mb-5 space-y-4 p-6">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-950 dark:text-brand-400">
                <User2 className="h-4 w-4" />
              </div>
              <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Personal information</h2>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Field label="Age">
                <input
                  type="number"
                  value={profile.age ?? ""}
                  onChange={(e) => setProfile({ ...profile, age: e.target.value ? Number(e.target.value) : null })}
                  className="input"
                  placeholder="e.g. 32"
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
                  placeholder="e.g. 170"
                />
              </Field>
              <Field label="Weight (kg)">
                <input
                  type="number"
                  value={profile.weight_kg ?? ""}
                  onChange={(e) => setProfile({ ...profile, weight_kg: e.target.value ? Number(e.target.value) : null })}
                  className="input"
                  placeholder="e.g. 65"
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
              <div className="flex items-end">
                {bmi ? (
                  <div className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm ${bmi.tone}`}>
                    <span className="font-medium">BMI {bmi.value}</span>
                    <span className="text-xs">{bmi.label}</span>
                  </div>
                ) : (
                  <p className="text-xs text-ink-400 dark:text-ink-500">
                    Add height + weight to see your BMI here.
                  </p>
                )}
              </div>
            </div>
          </Card>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Reveal delay={80}>
            <Card className="h-full space-y-4 p-6">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-red-50 text-red-600 dark:bg-red-950/60 dark:text-red-400">
                  <HeartPulse className="h-4 w-4" />
                </div>
                <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Medical history</h2>
              </div>
              <Field label="Known conditions (comma-separated)">
                <input
                  value={listToText(profile.known_conditions)}
                  onChange={(e) => setProfile({ ...profile, known_conditions: textToList(e.target.value) })}
                  className="input"
                  placeholder="e.g. asthma, hypertension"
                />
                <ChipPreview items={profile.known_conditions} />
              </Field>
              <Field label="Relevant medical history (comma-separated)">
                <input
                  value={listToText(profile.medical_history)}
                  onChange={(e) => setProfile({ ...profile, medical_history: textToList(e.target.value) })}
                  className="input"
                  placeholder="e.g. appendectomy 2019"
                />
                <ChipPreview items={profile.medical_history} />
              </Field>
            </Card>
          </Reveal>

          <Reveal delay={120}>
            <Card className="h-full space-y-4 p-6">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400">
                  <Pill className="h-4 w-4" />
                </div>
                <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Medications & allergies</h2>
              </div>
              <Field label="Current medications (comma-separated)">
                <input
                  value={listToText(profile.medications)}
                  onChange={(e) => setProfile({ ...profile, medications: textToList(e.target.value) })}
                  className="input"
                  placeholder="e.g. metformin, atorvastatin"
                />
                <ChipPreview items={profile.medications} />
              </Field>
              <Field label="Known drug allergies (comma-separated)">
                <input
                  value={listToText(profile.allergies)}
                  onChange={(e) => setProfile({ ...profile, allergies: textToList(e.target.value) })}
                  className="input"
                  placeholder="e.g. penicillin"
                />
                <ChipPreview items={profile.allergies} />
              </Field>
              {profile.allergies.length > 0 && (
                <div className="flex items-start gap-2 rounded-xl bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
                  <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    Dr Doom's medication safety checks will flag conflicts with these allergies automatically
                    whenever you ask about a drug.
                  </span>
                </div>
              )}
            </Card>
          </Reveal>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Reveal delay={160}>
            <Card className="h-full space-y-4 p-6">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-50 text-violet-600 dark:bg-violet-950/60 dark:text-violet-400">
                  <Activity className="h-4 w-4" />
                </div>
                <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Lifestyle</h2>
                <span className="ml-auto text-[10px] font-medium uppercase tracking-wide text-ink-400">Optional context</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Smoking status">
                  <select
                    value={lifestyle.smoking ?? ""}
                    onChange={(e) => setLifestyle("smoking", e.target.value)}
                    className="input"
                  >
                    <option value="">Not specified</option>
                    <option value="never">Never smoked</option>
                    <option value="former">Former smoker</option>
                    <option value="current">Current smoker</option>
                  </select>
                </Field>
                <Field label="Alcohol use">
                  <select
                    value={lifestyle.alcohol ?? ""}
                    onChange={(e) => setLifestyle("alcohol", e.target.value)}
                    className="input"
                  >
                    <option value="">Not specified</option>
                    <option value="none">None</option>
                    <option value="occasional">Occasional</option>
                    <option value="regular">Regular</option>
                  </select>
                </Field>
                <Field label="Exercise frequency">
                  <select
                    value={lifestyle.exercise ?? ""}
                    onChange={(e) => setLifestyle("exercise", e.target.value)}
                    className="input"
                  >
                    <option value="">Not specified</option>
                    <option value="sedentary">Rarely / sedentary</option>
                    <option value="light">1-2× a week</option>
                    <option value="active">3-5× a week</option>
                    <option value="athlete">Daily / athlete</option>
                  </select>
                </Field>
                <Field label="Diet notes">
                  <input
                    value={lifestyle.diet ?? ""}
                    onChange={(e) => setLifestyle("diet", e.target.value)}
                    className="input"
                    placeholder="e.g. vegetarian, low-sodium"
                  />
                </Field>
              </div>
            </Card>
          </Reveal>

          <Reveal delay={200}>
            <Card className="h-full space-y-4 p-6">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50 text-sky-600 dark:bg-sky-950/60 dark:text-sky-400">
                  <PhoneCall className="h-4 w-4" />
                </div>
                <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-100">Emergency contact</h2>
                <span className="ml-auto text-[10px] font-medium uppercase tracking-wide text-ink-400">Kept private</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Name">
                  <input
                    value={emergencyContact.name ?? ""}
                    onChange={(e) => setEmergencyContact("name", e.target.value)}
                    className="input"
                    placeholder="e.g. Jordan Lee"
                  />
                </Field>
                <Field label="Relationship">
                  <input
                    value={emergencyContact.relationship ?? ""}
                    onChange={(e) => setEmergencyContact("relationship", e.target.value)}
                    className="input"
                    placeholder="e.g. Spouse"
                  />
                </Field>
                <Field label="Phone number">
                  <input
                    value={emergencyContact.phone ?? ""}
                    onChange={(e) => setEmergencyContact("phone", e.target.value)}
                    className="input"
                    placeholder="e.g. +1 555 010 2020"
                  />
                </Field>
              </div>
              <p className="text-[11px] text-ink-400 dark:text-ink-500">
                This is stored for your own reference only — Dr Doom never contacts anyone automatically. In
                a genuine emergency, always call your local emergency number directly.
              </p>
            </Card>
          </Reveal>
        </div>

        <Reveal delay={240} className="mt-5">
          <div className="flex flex-col-reverse items-stretch justify-between gap-3 sm:flex-row sm:items-center">
            <Button variant="danger" className="gap-1.5" onClick={deleteAll}>
              <Trash2 className="h-4 w-4" /> Delete my health data
            </Button>
            <Button className="gap-1.5" onClick={save} disabled={saving}>
              {saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}
              {saving ? "Saving…" : saved ? "Saved!" : "Save changes"}
            </Button>
          </div>
        </Reveal>

        <Reveal delay={280} className="mt-6">
          <Card className="flex items-start gap-3 border-brand-200/70 bg-brand-50/50 p-4 dark:border-brand-900 dark:bg-brand-950/30">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-brand-600 dark:text-brand-400" />
            <p className="text-xs leading-relaxed text-ink-600 dark:text-ink-400">
              The more Dr Doom already knows, the fewer intake questions it needs to ask during a
              consultation — a complete profile means faster, more personalized assessments from your very
              first message.
            </p>
          </Card>
        </Reveal>
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
