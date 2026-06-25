/**
 * Typed client for the TinyGuide AI backend microservice (port 8000).
 *
 * Keeps every fetch in one place with strict request/response contracts so the
 * UI never hand-rolls untyped `fetch` calls.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Gender = "male" | "female" | "other";

export interface Infant {
  id: string;
  name: string;
  birth_date: string; // ISO date
  gender: Gender;
}

export interface InfantCreate {
  name: string;
  birth_date: string;
  gender: Gender;
}

export interface GrowthInput {
  gender: Gender;
  age_months: number;
  weight_kg?: number;
  height_cm?: number;
}

export interface MetricResult {
  metric: string;
  z_score: number;
  percentile: number;
  reference_median: number;
  interpretation: string;
}

export interface GrowthResult {
  age_months: number;
  results: MetricResult[];
}

export interface Milestone {
  id: string;
  title: string;
  category: string;
  typical_age_months: number;
  description: string;
  tips: string[];
}

export interface ScheduledVaccine {
  code: string;
  name: string;
  recommended_age_months: number;
}

/** Status of a milestone dose relative to today. */
export type VaccineStatus = "OVERDUE" | "UPCOMING" | "SAFE";

export interface VaccineDueItem {
  code: string;
  name: string;
  age_months: number;
  due_date: string; // ISO date
  status: VaccineStatus;
}

export interface InfantVaccineSchedule {
  infant_id: string;
  birth_date: string; // ISO date
  generated_on: string; // ISO date
  items: VaccineDueItem[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** Answer language for the AI assistant. */
export type AssistantLang = "en" | "ur" | "roman";

export interface AssistantResponse {
  answer: string;
  sources: string[];
  citations: string[];
  model: string;
  is_emergency: boolean;
  recommended_actions: string[];
}

export interface GrowthLogCreate {
  infant_id: string;
  weight_kg: number;
  height_cm: number;
  recorded_at?: string; // ISO date; defaults to today on the server
}

export interface GrowthLogEntry extends GrowthLogCreate {
  id: string;
  recorded_at: string; // ISO date
}

export interface GrowthTimelineInput {
  infant_id: string;
}

/** One timeline point: the child's value plus WHO percentile bands. */
export interface GrowthPlotPoint {
  age_months: number;
  child_weight: number;
  p5_weight: number;
  p50_weight: number;
  p95_weight: number;
}

export interface GrowthTimeline {
  gender: Gender;
  birth_date: string; // ISO date
  points: GrowthPlotPoint[];
}

/** Raised when the backend returns a non-2xx response. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

/** Strongly-typed endpoint wrappers. */
export const api = {
  registerInfant: (payload: InfantCreate) =>
    request<Infant>("/api/infants", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listInfants: () => request<Infant[]>("/api/infants"),

  updateInfant: (id: string, payload: InfantCreate) =>
    request<Infant>(`/api/infants/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  growthPercentile: (payload: GrowthInput) =>
    request<GrowthResult>("/api/analytics/growth-percentile", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listMilestones: (maxAgeMonths?: number) =>
    request<Milestone[]>(
      `/api/milestones${
        maxAgeMonths != null ? `?max_age_months=${maxAgeMonths}` : ""
      }`
    ),

  vaccineSchedule: () =>
    request<ScheduledVaccine[]>("/api/vaccinations/schedule"),

  infantVaccinations: (infantId: string) =>
    request<InfantVaccineSchedule>(
      `/api/vaccinations/${encodeURIComponent(infantId)}`
    ),

  growthTimeline: (payload: GrowthTimelineInput) =>
    request<GrowthTimeline>("/api/analytics/growth-timeline", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logGrowth: (payload: GrowthLogCreate) =>
    request<GrowthLogEntry>("/api/analytics/growth-log", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  askAssistant: (
    query: string,
    history: ChatMessage[] = [],
    language: AssistantLang = "en"
  ) =>
    request<AssistantResponse>("/api/assistant/ask", {
      method: "POST",
      body: JSON.stringify({ query, history, language }),
    }),
};
