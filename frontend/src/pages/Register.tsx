import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Stethoscope } from "lucide-react";
import { Button } from "@/components/common/Button";
import { useAuthStore } from "@/stores/authStore";

export function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { register, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    clearError();
    try {
      await register(email, password, fullName || undefined);
      navigate("/app");
    } catch {
      /* error shown via store */
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 dark:bg-ink-950 px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft">
            <Stethoscope className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-ink-900 dark:text-white">Create your account</h1>
          <p className="text-sm text-ink-500 dark:text-ink-400">Start your first evidence-grounded consultation</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-2xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-6 shadow-soft">
          {error && <p className="rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-700 dark:text-red-300">{error}</p>}
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600 dark:text-ink-300">Full name (optional)</label>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-xl border border-ink-200 dark:border-ink-700 bg-transparent px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600 dark:text-ink-300">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-ink-200 dark:border-ink-700 bg-transparent px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-600 dark:text-ink-300">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-ink-200 dark:border-ink-700 bg-transparent px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-brand-400"
            />
            <p className="mt-1 text-[11px] text-ink-500 dark:text-ink-400">At least 8 characters.</p>
          </div>
          <label className="flex items-start gap-2 text-xs text-ink-600 dark:text-ink-400">
            <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
            I understand Dr Doom provides educational health information, not medical diagnosis or treatment, and I
            consent to my data being processed to provide this service.
          </label>
          <Button type="submit" disabled={submitting || !consent} className="w-full">
            {submitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-500 dark:text-ink-400">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand-600 dark:text-brand-400">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
