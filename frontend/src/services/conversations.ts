import { api } from "@/services/api";
import type { ChatResponse, ConversationCard, ConversationDetail } from "@/types/api";

export interface ConversationStats {
  total_consultations: number;
  completed: number;
  in_progress: number;
  urgent_flagged: number;
  top_concerns: { name: string; count: number }[];
  last_consultation_at: string | null;
}

export const conversationsApi = {
  list: () => api.get<ConversationCard[]>("/api/conversations"),
  stats: () => api.get<ConversationStats>("/api/conversations/stats/overview"),
  get: (id: string) => api.get<ConversationDetail>(`/api/conversations/${id}`),
  rename: (id: string, title: string) => api.patch<ConversationCard>(`/api/conversations/${id}`, { title }),
  remove: (id: string) => api.delete<void>(`/api/conversations/${id}`),
};

export const chatApi = {
  send: (payload: {
    conversation_id?: string | null;
    message: string;
    answer_question_id?: string | null;
    answer_value?: string | number | string[] | null;
  }) => api.post<ChatResponse>("/api/chat", payload),
};
