import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import {
  Stethoscope,
  MessageSquarePlus,
  History,
  User,
  Settings,
  LogOut,
  Moon,
  Sun,
  ShieldCheck,
  Home,
} from "lucide-react";
import clsx from "clsx";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";

const NAV_ITEMS = [
  { to: "/app", label: "Dashboard", icon: Home, end: true },
  { to: "/app/chat", label: "New consultation", icon: MessageSquarePlus, end: false },
  { to: "/app/history", label: "History", icon: History, end: true },
  { to: "/app/profile", label: "Health profile", icon: User, end: true },
  { to: "/app/settings", label: "Settings", icon: Settings, end: true },
];

export function AppLayout() {
  const { user, status, fetchMe, logout } = useAuthStore();
  const { theme, toggle } = useThemeStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (status === "idle") fetchMe();
  }, [status, fetchMe]);

  useEffect(() => {
    if (status === "ready" && !user) navigate("/login");
  }, [status, user, navigate]);

  if (status !== "ready" || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink-50 dark:bg-ink-950">
        <Stethoscope className="h-6 w-6 animate-pulse text-brand-500" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-ink-50 dark:bg-ink-950">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-ink-200/70 dark:border-ink-800 bg-white dark:bg-ink-900">
        <Link to="/app" className="flex items-center gap-2 px-5 py-5 transition-opacity hover:opacity-80">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-soft">
            <Stethoscope className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight">DR DOOM</p>
            <p className="text-[10px] text-ink-500 dark:text-ink-400 leading-tight">Evidence-grounded AI</p>
          </div>
        </Link>

        <nav className="flex-1 space-y-1 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
                    : "text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
          {user.is_admin && (
            <NavLink
              to="/app/admin"
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
                    : "text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800"
                )
              }
            >
              <ShieldCheck className="h-4 w-4" />
              Admin diagnostics
            </NavLink>
          )}
        </nav>

        <div className="space-y-1 border-t border-ink-200/70 dark:border-ink-800 p-3">
          <button
            type="button"
            onClick={toggle}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <button
            type="button"
            onClick={async () => {
              // logout() never throws (see authStore) — clears local auth
              // state regardless of whether the server call succeeded, so
              // this navigation always runs and the user is never stuck.
              await logout();
              navigate("/");
            }}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </div>

      {/* Mobile bottom nav (§59) */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 flex md:hidden items-center justify-around border-t border-ink-200 dark:border-ink-800 bg-white/95 dark:bg-ink-900/95 backdrop-blur py-2">
        {[
          { to: "/app", icon: Home, label: "Home", end: true },
          { to: "/app/chat", icon: MessageSquarePlus, label: "Chat", end: false },
          { to: "/app/history", icon: History, label: "History", end: true },
          { to: "/app/profile", icon: User, label: "Profile", end: true },
        ].map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              clsx(
                "flex flex-col items-center gap-0.5 px-3 py-1 text-[10px] font-medium",
                isActive ? "text-brand-600 dark:text-brand-400" : "text-ink-500 dark:text-ink-400"
              )
            }
          >
            <item.icon className="h-5 w-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
