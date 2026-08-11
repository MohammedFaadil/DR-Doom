import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Stethoscope } from "lucide-react";
import { Button } from "@/components/common/Button";
import { useAuthStore } from "@/stores/authStore";

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    clearError();
    try {
      await login(email, password);
      navigate("/app");
    } catch {
      /* error shown via store */
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 dark:bg-ink-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft">
            <Stethoscope className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-ink-900 dark:text-white">Welcome back</h1>
          <p className="text-sm text-ink-500 dark:text-ink-400">Sign in to continue your consultation</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-2xl border border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900 p-6 shadow-soft">
          {error && <p className="rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-700 dark:text-red-300">{error}</p>}
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-ink-200 dark:border-ink-700 bg-transparent px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-500 dark:text-ink-400">
          Don't have an account?{" "}
          <Link to="/register" className="font-medium text-brand-600 dark:text-brand-400">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
