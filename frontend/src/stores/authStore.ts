import { create } from "zustand";
import { api, ApiError } from "@/services/api";
import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "ready";
  error: string | null;
  fetchMe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "idle",
  error: null,

  fetchMe: async () => {
    set({ status: "loading" });
    try {
      const user = await api.get<User>("/api/auth/me");
      set({ user, status: "ready" });
    } catch {
      set({ user: null, status: "ready" });
    }
  },

  login: async (email, password) => {
    set({ error: null });
    try {
      const user = await api.post<User>("/api/auth/login", { email, password });
      set({ user });
    } catch (e) {
      set({ error: e instanceof ApiError ? e.message : "Unable to sign in." });
      throw e;
    }
  },

  register: async (email, password, fullName) => {
    set({ error: null });
    try {
      const user = await api.post<User>("/api/auth/register", { email, password, full_name: fullName || null });
      set({ user });
    } catch (e) {
      set({ error: e instanceof ApiError ? e.message : "Unable to create account." });
      throw e;
    }
  },

  logout: async () => {
    await api.post("/api/auth/logout");
    set({ user: null });
  },

  deleteAccount: async () => {
    await api.delete("/api/auth/me");
    set({ user: null });
  },

  clearError: () => set({ error: null }),
}));
