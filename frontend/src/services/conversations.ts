import { api, API_URL, ApiError } from "@/services/api";
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

export interface ChatPayload {
  conversation_id?: string | null;
  message: string;
  answer_question_id?: string | null;
  answer_value?: string | number | string[] | null;
}

export interface StreamCallbacks {
  onStatus?: (stage: string, message: string) => void;
  onToken?: (text: string) => void;
  onFinal?: (response: ChatResponse) => void;
}

export const chatApi = {
  send: (payload: ChatPayload) => api.post<ChatResponse>("/api/chat", payload),

  // Consumes the SSE stream from /api/chat/stream. The full retrieval ->
  // generation -> grounding-validation pipeline runs server-side first
  // (see backend/app/api/chat.py::_chunk_for_streaming for why — raw model
  // tokens are never shown before they've been safety-checked), then the
  // validated answer arrives as a sequence of "token" events for a
  // progressive typing effect, followed by one "final" event carrying the
  // full structured ChatResponse (citations, question payload, etc.).
  sendStream: async (payload: ChatPayload, callbacks: StreamCallbacks, signal?: AbortSignal): Promise<void> => {
    const res = await fetch(`${API_URL}/api/chat/stream`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok || !res.body) {
      let detail = "Something went wrong. Please try again.";
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(res.status, detail);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const raw of events) {
        let eventName = "message";
        let dataStr = "";
        for (const line of raw.split("\n")) {
          if (line.startsWith("event: ")) eventName = line.slice(7);
          else if (line.startsWith("data: ")) dataStr += line.slice(6);
        }
        if (!dataStr) continue;

        let data: Record<string, unknown>;
        try {
          data = JSON.parse(dataStr);
        } catch {
          continue;
        }

        if (eventName === "status") callbacks.onStatus?.(data.stage as string, data.message as string);
        else if (eventName === "token") callbacks.onToken?.(data.text as string);
        else if (eventName === "final") callbacks.onFinal?.(data as unknown as ChatResponse);
      }
    }
  },
};
