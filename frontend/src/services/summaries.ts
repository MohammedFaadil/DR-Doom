import { api } from "@/services/api";
import type { ConsultationSummary } from "@/types/api";

export const summariesApi = {
  list: () => api.get<ConsultationSummary[]>("/api/summaries"),
  get: (id: string) => api.get<ConsultationSummary>(`/api/summaries/${id}`),
  remove: (id: string) => api.delete<void>(`/api/summaries/${id}`),
  pdfUrl: (id: string) => `/api/summaries/${id}/pdf`,
};
