import { create } from "zustand";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

function initialTheme(): Theme {
  // Light is the default regardless of OS/browser preference — only an
  // explicit user choice (saved below) switches to dark.
  const stored = localStorage.getItem("drdoom-theme") as Theme | null;
  return stored === "dark" ? "dark" : "light";
}

interface ThemeState {
  theme: Theme;
  toggle: () => void;
  set: (t: Theme) => void;
}

const initial = initialTheme();
applyTheme(initial);

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initial,
  toggle: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("drdoom-theme", next);
    applyTheme(next);
    set({ theme: next });
  },
  set: (t) => {
    localStorage.setItem("drdoom-theme", t);
    applyTheme(t);
    set({ theme: t });
  },
}));
