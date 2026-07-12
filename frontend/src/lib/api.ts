import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("agora_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401 (invalid/expired token) or 403 (no token at all —
// FastAPI's HTTPBearer security scheme returns 403, not 401, when the
// Authorization header is simply missing). Without handling 403 here, a
// logged-out user sees the dashboard shell render normally while every
// individual page's data fetch silently fails, with no indication that
// they need to log in again.
//
// Auth endpoints themselves are excluded: a 401/403 from /auth/login (bad
// credentials, deactivated account) is a message to show inline on the
// login form, not a session-expiry redirect — and redirecting away from
// the login page while the user is actively trying to log in would wipe
// out that error message before they ever saw it.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    const url: string = err.config?.url || "";
    const isAuthEndpoint = url.startsWith("/auth/");
    if (
      !isAuthEndpoint &&
      (err.response?.status === 401 || err.response?.status === 403) &&
      typeof window !== "undefined"
    ) {
      localStorage.removeItem("agora_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// ─── Typed API methods ────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  register: (email: string, password: string, full_name: string) =>
    api.post("/auth/register", { email, password, full_name }),
};

export const analyticsApi = {
  overview: (days = 30) => api.get(`/analytics/overview?days=${days}`),
  engagement: (days = 30) => api.get(`/analytics/engagement?days=${days}`),
  geography: () => api.get("/analytics/geography"),
  trend: (metric: string, days = 90) =>
    api.get(`/analytics/trend/${metric}?days=${days}`),
  snapshot: () => api.post("/analytics/snapshot"),
};

export const participantsApi = {
  register: (data: object) => api.post("/participants", data),
  list: (params?: object) => api.get("/participants", { params }),
  count: () => api.get("/participants/count"),
};

export const eventsApi = {
  list: (params?: object) => api.get("/events", { params }),
  create: (data: object) => api.post("/events", data),
  attend: (event_id: number, participant_id: number) =>
    api.post("/events/attend", { event_id, participant_id }),
};

export const engagementApi = {
  summary: (days = 30) => api.get(`/engagement/summary?days=${days}`),
  record: (data: object) => api.post("/engagement", data),
};

export const socialApi = {
  overview: () => api.get("/social/overview"),
  sentiment: (days = 30) => api.get(`/social/sentiment?days=${days}`),
  topics: (days = 7, limit = 20) =>
    api.get(`/social/topics?days=${days}&limit=${limit}`),
  ingest: (query: string, platforms?: string) =>
    api.post(`/social/ingest?query=${encodeURIComponent(query)}${platforms ? `&platforms=${platforms}` : ""}`),
};

export const reportsApi = {
  list: () => api.get("/reports"),
  get: (id: number) => api.get(`/reports/${id}`),
  generate: (data: object) => api.post("/reports/generate", data),
};

export const intelligenceApi = {
  sentimentTrends: (days = 30, platform?: string) =>
    api.get(`/intelligence/sentiment-trends?days=${days}${platform ? `&platform=${platform}` : ""}`),
  entities: (days = 7, label?: string, limit = 20) =>
    api.get(`/intelligence/entities?days=${days}&limit=${limit}${label ? `&label=${label}` : ""}`),
  narratives: (days = 30) => api.get(`/intelligence/narratives?days=${days}`),
  sourceComparison: (days = 30) => api.get(`/intelligence/source-comparison?days=${days}`),
  trendVelocity: (days = 14) => api.get(`/intelligence/trend-velocity?days=${days}`),
  emergingTopics: (days = 7) => api.get(`/intelligence/emerging-topics?days=${days}`),
  normalisationStats: () => api.get("/intelligence/normalisation-stats"),
  triggerProcessing: () => api.post("/intelligence/process"),
};

export const briefingApi = {
  executive: (days = 7) => api.get(`/briefing/executive?days=${days}`),
};

export const dataHealthApi = {
  overview: () => api.get("/data-health/overview"),
  connectors: (hours = 24) => api.get(`/data-health/connectors?hours=${hours}`),
  ingestionVolume: (days = 30) => api.get(`/data-health/ingestion-volume?days=${days}`),
  jobs: (limit = 20) => api.get(`/data-health/jobs?limit=${limit}`),
  errors: (hours = 24) => api.get(`/data-health/errors?hours=${hours}`),
};
