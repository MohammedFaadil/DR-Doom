import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { PanelRightClose, PanelRightOpen, Stethoscope, Sparkles, Zap } from "lucide-react";
import { MessageBubble, DisplayMessage } from "@/components/chat/MessageBubble";
import { Composer } from "@/components/chat/Composer";
import { AssessmentPanel } from "@/components/chat/AssessmentPanel";
import { EmergencyBanner } from "@/components/chat/EmergencyBanner";
import { SummaryActions } from "@/components/chat/SummaryActions";
import { chatApi, conversationsApi } from "@/services/conversations";
import type { ChatResponse, Citation, Question } from "@/types/api";

function uid() {
  return Math.random().toString(36).slice(2);
}

// Purely informational — lets the patient see what's actually generating
// their answer (a real hosted LLM vs. the deterministic template
// fallback), not a claim about the answer's safety: every provider's
// output passes through the same GroundingValidator either way.
const PROVIDER_LABELS: Record<string, string> = {
  groq: "Groq · Llama 3.3 70B",
  llama_cpp: "Local model",
  local_transformers: "Local model",
  ollama: "Ollama",
};

function ProviderBadge({ provider }: { provider?: string }) {
  if (!provider || provider === "template" || provider === "template_fallback") return null;
  const label = PROVIDER_LABELS[provider] || provider;
  return (
    <span className="hidden items-center gap-1 rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-700 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-300 sm:inline-flex">
      <Zap className="h-2.5 w-2.5" />
      {label}
    </span>
  );
}

const STARTER_PROMPTS = [
  "I've had a headache since this morning",
  "I have a sore throat and fever",
  "What causes migraines?",
  "Tell me about ibuprofen",
];

const WELCOME_MESSAGE =
  "Hi, I'm **Dr Doom**. Tell me what you're experiencing and I'll ask a few focused questions " +
  "before sharing any evidence-grounded guidance.\n\nYou can also ask a direct health question, " +
  "or use the microphone to speak instead of typing.";

export function Chat() {
  const { conversationId: routeId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [conversationId, setConversationId] = useState<string | undefined>(routeId);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [isEmergency, setIsEmergency] = useState(false);
  const [riskLevel, setRiskLevel] = useState("unknown");
  const [patientState, setPatientState] = useState<ChatResponse["patient_state"]>({});
  const [evidence, setEvidence] = useState<Citation[]>([]);
  const [groundingConfidence, setGroundingConfidence] = useState<number | undefined>(undefined);
  const [activeProvider, setActiveProvider] = useState<string | undefined>(undefined);
  const [summary, setSummary] = useState<ChatResponse["summary"]>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(!!routeId);
  const bottomRef = useRef<HTMLDivElement>(null);

  // The conversation id has to be readable from inside stable callbacks
  // (the auto-send effect below runs once and must not re-fire when state
  // changes), so it's mirrored into a ref alongside the state.
  const conversationIdRef = useRef<string | undefined>(routeId);
  useEffect(() => {
    conversationIdRef.current = conversationId;
  }, [conversationId]);

  // ── Load existing conversation, or show the welcome state ──
  useEffect(() => {
    if (!routeId) {
      setMessages([{ id: uid(), role: "assistant", content: WELCOME_MESSAGE }]);
      setLoadingHistory(false);
      return;
    }
    let cancelled = false;
    conversationsApi
      .get(routeId)
      .then((detail) => {
        if (cancelled) return;
        setConversationId(detail.id);
        setIsEmergency(detail.is_emergency);
        setRiskLevel(detail.risk_level);
        setPatientState(detail.patient_state as ChatResponse["patient_state"]);
        const loaded = detail.messages.map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          messageType: m.message_type,
          question: m.message_type === "question" ? m.payload?.question || null : null,
        }));
        const lastIndex = loaded.length - 1;
        setMessages(
          loaded.map((m, i) => ({
            ...m,
            // Only the most recent question is still answerable; older ones
            // are marked answered so their option buttons render disabled.
            answered: m.question ? i !== lastIndex : true,
          }))
        );
        setLoadingHistory(false);
      })
      .catch(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [routeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // Finalizes the placeholder streaming bubble in place (by id) with the
  // full validated ChatResponse, rather than appending a new message —
  // this is what makes tokens "become" the final answer instead of a
  // second message popping in after the streamed one.
  const finalizeStreamingMessage = useCallback(
    (streamingId: string, result: ChatResponse) => {
      setConversationId(result.conversation_id);
      conversationIdRef.current = result.conversation_id;
      setIsEmergency(result.is_emergency);
      setRiskLevel(result.risk_level);
      setPatientState(result.patient_state || {});
      setSummary(result.summary);

      if (result.evidence?.length) {
        setEvidence((prev) => {
          const seen = new Set(prev.map((e) => e.url));
          return [...prev, ...result.evidence.filter((e) => !seen.has(e.url))];
        });
      }
      if (result.grounding_confidence > 0) setGroundingConfidence(result.grounding_confidence);
      setActiveProvider(result.model_provider);

      setMessages((prev) =>
        prev.map((m) => {
          if (m.id === streamingId) {
            return {
              ...m,
              content: result.message,
              messageType: result.response_type,
              question: result.question,
              evidence: result.evidence,
              isEmergency: result.is_emergency,
              groundingConfidence: result.grounding_confidence,
              streaming: false,
            };
          }
          // A question that has just been answered can't be answered again.
          return m.question ? { ...m, answered: true } : m;
        })
      );

      if (!routeId) navigate(`/app/chat/${result.conversation_id}`, { replace: true });
    },
    [navigate, routeId]
  );

  const streamTurn = useCallback(
    async (payload: { message: string; answer_question_id?: string; answer_value?: string | number | string[] }) => {
      const streamingId = uid();
      setMessages((prev) => [...prev, { id: streamingId, role: "assistant", content: "", streaming: true }]);
      setSending(true);
      try {
        await chatApi.sendStream({ conversation_id: conversationIdRef.current, ...payload }, {
          onToken: (text) => {
            setMessages((prev) => prev.map((m) => (m.id === streamingId ? { ...m, content: m.content + text } : m)));
          },
          onFinal: (result) => finalizeStreamingMessage(streamingId, result),
        });
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === streamingId
              ? { ...m, content: "Dr Doom is having trouble processing that right now. Please try again in a moment.", streaming: false }
              : m
          )
        );
      } finally {
        setSending(false);
      }
    },
    [finalizeStreamingMessage]
  );

  const sendMessage = useCallback(
    async (text: string) => {
      setMessages((prev) => [...prev, { id: uid(), role: "user", content: text }]);
      await streamTurn({ message: text });
    },
    [streamTurn]
  );

  // Dashboard "try asking" links arrive as /app/chat?q=... — send once, then
  // strip the param so a refresh doesn't resend it.
  const autoSentRef = useRef(false);
  useEffect(() => {
    const prefill = searchParams.get("q");
    if (!prefill || routeId || autoSentRef.current) return;
    autoSentRef.current = true;
    setSearchParams({}, { replace: true });
    void sendMessage(prefill);
  }, [searchParams, routeId, setSearchParams, sendMessage]);

  async function answerQuestion(question: Question, args: { label: string; value: string | number | string[] }) {
    setMessages((prev) => [
      ...prev.map((m) => (m.question?.id === question.id ? { ...m, answered: true } : m)),
      { id: uid(), role: "user", content: args.label },
    ]);
    await streamTurn({ message: args.label, answer_question_id: question.id, answer_value: args.value });
  }

  function startNew() {
    navigate("/app/chat");
    setConversationId(undefined);
    conversationIdRef.current = undefined;
    setMessages([{ id: uid(), role: "assistant", content: WELCOME_MESSAGE }]);
    setIsEmergency(false);
    setRiskLevel("unknown");
    setPatientState({});
    setEvidence([]);
    setGroundingConfidence(undefined);
    setSummary(null);
  }

  if (loadingHistory) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Stethoscope className="h-6 w-6 animate-pulse text-brand-500" />
      </div>
    );
  }

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
  const isComplete = lastAssistant?.messageType === "assessment";
  const showStarters = messages.length === 1 && !sending;

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex flex-1 flex-col overflow-hidden">
        {isEmergency && <EmergencyBanner />}

        <div className="flex items-center justify-between border-b border-ink-200/70 dark:border-ink-800 bg-white/60 dark:bg-ink-900/60 px-5 py-3 backdrop-blur">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Stethoscope className="h-3.5 w-3.5" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-ink-800 dark:text-ink-100">Consultation</p>
              {patientState.symptoms && patientState.symptoms.length > 0 && (
                <p className="text-[11px] capitalize text-ink-500 dark:text-ink-400">
                  {patientState.symptoms.map((s) => s.name).join(", ")}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ProviderBadge provider={activeProvider} />
            <button
              type="button"
              onClick={startNew}
              className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-ink-500 transition-colors hover:bg-ink-100 dark:hover:bg-ink-800"
            >
              New
            </button>
            <button
              type="button"
              onClick={() => setPanelOpen((v) => !v)}
              className="hidden items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-ink-500 transition-colors hover:bg-ink-100 dark:hover:bg-ink-800 md:flex"
            >
              {panelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
              Assessment
            </button>
          </div>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto scrollbar-thin bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(11,191,166,0.06),transparent)] px-5 py-6 pb-28 dark:bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(11,191,166,0.10),transparent)] md:pb-6">
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              answering={sending}
              onAnswer={(args) => m.question && answerQuestion(m.question, args)}
            />
          ))}

          {showStarters && (
            <div className="animate-fade-up pl-11">
              <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                <Sparkles className="h-3 w-3" /> Try one of these
              </p>
              <div className="flex flex-wrap gap-2">
                {STARTER_PROMPTS.map((p, i) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => sendMessage(p)}
                    style={{ animationDelay: `${i * 60}ms` }}
                    className="animate-fade-up rounded-xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-900 px-3.5 py-2 text-sm text-ink-600 shadow-soft transition-all hover:-translate-y-0.5 hover:border-brand-400 hover:text-brand-700 dark:text-ink-300 dark:hover:text-brand-300"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {isComplete && conversationId && (
            <SummaryActions conversationId={conversationId} summary={summary} onNewConsultation={startNew} />
          )}
          <div ref={bottomRef} />
        </div>

        <div className="mb-16 border-t border-ink-200/70 dark:border-ink-800 bg-white/80 px-5 py-4 backdrop-blur dark:bg-ink-900/80 md:mb-0">
          <Composer onSend={sendMessage} disabled={sending} />
          <p className="mt-2 text-center text-[10px] text-ink-400">
            Dr Doom provides educational information, not a diagnosis. In an emergency, call your local emergency number.
          </p>
        </div>
      </div>

      {panelOpen && (
        <aside className="hidden w-96 shrink-0 border-l border-ink-200/70 bg-white dark:border-ink-800 dark:bg-ink-900 md:block">
          <AssessmentPanel
            patientState={patientState}
            riskLevel={riskLevel}
            evidence={evidence}
            groundingConfidence={groundingConfidence}
          />
        </aside>
      )}
    </div>
  );
}
