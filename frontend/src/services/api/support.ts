import { createHttpClient } from "./http";

export type FeedbackCategory =
  | "incidente"
  | "mejora"
  | "usabilidad"
  | "rendimiento"
  | "consulta";

export type FeedbackPriority = "baja" | "media" | "alta" | "critica";
export type FeedbackStatus = "abierto" | "en_progreso" | "resuelto" | "descartado";

export type FeedbackPayload = {
  module: string;
  category: FeedbackCategory;
  priority: FeedbackPriority;
  title: string;
  description: string;
  contact?: string;
  metadata?: Record<string, unknown>;
  usage_context?: Record<string, unknown>;
};

export type FeedbackResponse = FeedbackPayload & {
  id: number;
  tracking_id: string;
  status: FeedbackStatus;
  created_at: string;
  updated_at: string;
  resolution_notes?: string | null;
};

export type FeedbackSummary = {
  tracking_id: string;
  title: string;
  module: string;
  category: FeedbackCategory;
  priority: FeedbackPriority;
  status: FeedbackStatus;
  created_at: string;
  updated_at: string;
};

export type FeedbackHotspot = {
  module: string;
  interactions_last_30d: number;
  open_feedback: number;
  priority_score: number;
};

export type FeedbackMetrics = {
  totals: Record<string, number>;
  by_category: Record<FeedbackCategory, number>;
  by_priority: Record<FeedbackPriority, number>;
  by_status: Record<FeedbackStatus, number>;
  hotspots: FeedbackHotspot[];
  recent_feedback: FeedbackSummary[];
};

const http = createHttpClient();

export async function submitFeedback(payload: FeedbackPayload): Promise<FeedbackResponse> {
  const { data } = await http.post<FeedbackResponse>("/support/feedback", payload);
  return data;
}

export async function fetchFeedbackMetrics(): Promise<FeedbackMetrics> {
  const { data } = await http.get<FeedbackMetrics>("/support/feedback/metrics");
  return data;
}
