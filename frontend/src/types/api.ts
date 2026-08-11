export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  preferred_language: string;
}

export interface HealthProfile {
  id: string;
  age: number | null;
  sex: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  allergies: string[];
  known_conditions: string[];
  medications: string[];
  medical_history: string[];
  pregnancy_status: string | null;
  lifestyle: Record<string, unknown>;
  emergency_contact: Record<string, unknown> | null;
}

export type QuestionType = "single_select" | "multi_select" | "numeric" | "date" | "text" | "yes_no" | "slider";

export interface QuestionOption {
  label: string;
  value: string;
}

export interface Question {
  id: string;
  question: string;
  type: QuestionType;
  options?: QuestionOption[];
  reason: string;
  clinical_priority: number;
  field: string;
}

export interface Citation {
  title: string;
  organization: string;
  url: string;
  score?: number;
}

export type ResponseType = "question" | "text" | "emergency" | "assessment" | "summary" | "insufficient_evidence";

export interface ConsultationSummary {
  id?: string;
  conversation_id?: string;
  conversation_title?: string;
  patient_profile: { age: number | null; sex: string | null; pregnancy_status: string | null };
  primary_concern: string | null;
  symptoms: string[];
  duration: string | null;
  severity: string | number | null;
  associated_symptoms: string[];
  relevant_history: string[];
  medications: string[];
  allergies: string[];
  red_flags: string[];
  risk_level: string;
  evidence_consulted: Citation[];
  guidance_provided: string | null;
  recommended_next_step: string | null;
  unanswered_questions: string[];
  disclaimer: string;
  created_at?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  message_type: string;
  payload: { question?: Question } | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  state: string;
  risk_level: string;
  is_emergency: boolean;
  is_complete: boolean;
  patient_state: Record<string, unknown>;
  messages: ChatMessage[];
}

export interface ConversationCard {
  id: string;
  title: string;
  primary_complaint: string | null;
  risk_level: string;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  response_type: ResponseType;
  message: string;
  question: Question | null;
  evidence: Citation[];
  is_emergency: boolean;
  risk_level: string;
  conversation_state: string;
  model_provider: string;
  summary: ConsultationSummary | null;
  patient_state: {
    age?: number | null;
    sex?: string | null;
    symptoms?: { name: string; duration?: string | null; severity?: number | null }[];
    missing_information?: string[];
    [key: string]: unknown;
  };
}
