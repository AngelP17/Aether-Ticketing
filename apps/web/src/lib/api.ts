import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api",
});

export const ticketsApi = {
  list: (params?: Record<string, string | number>) =>
    api.get("/tickets", { params }),
  get: (ticketId: string) =>
    api.get(`/tickets/${ticketId}`),
  getEvents: (ticketId: string) =>
    api.get(`/tickets/${ticketId}/events`),
};

export const incidentsApi = {
  list: () => api.get("/incidents"),
  get: (incidentId: string) => api.get(`/incidents/${incidentId}`),
};

export const decisionsApi = {
  recompute: (ticketId: string) =>
    api.post(`/decisions/recompute/${ticketId}`),
};

export const recommendationsApi = {
  accept: (id: number, note?: string) =>
    api.post(`/recommendations/${id}/accept`, { note }),
  reject: (id: number, reason?: string) =>
    api.post(`/recommendations/${id}/reject`, { reason }),
  override: (id: number, note: string, priority?: number) =>
    api.post(`/recommendations/${id}/override`, { override_note: note, override_priority: priority }),
};

export const reportsApi = {
  excel: (params?: Record<string, string>) =>
    api.get("/reports/excel", { params, responseType: "blob" }),
};

export const metricsApi = {
  get: () => api.get("/metrics"),
};

export const authApi = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
};
