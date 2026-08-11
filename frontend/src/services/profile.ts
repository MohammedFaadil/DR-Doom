import { api } from "@/services/api";
import type { HealthProfile } from "@/types/api";

export const profileApi = {
  get: () => api.get<HealthProfile>("/api/profile"),
  update: (payload: Partial<HealthProfile>) => api.put<HealthProfile>("/api/profile", payload),
  remove: () => api.delete<void>("/api/profile"),
};
