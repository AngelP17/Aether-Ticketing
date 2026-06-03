import axios from "axios";

import { ACCESS_TOKEN_KEY } from "@/lib/auth";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api",
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const ticketsApi = {
  list: (params?: Record<string, string | number>) =>
    api.get("/tickets", { params }),
  get: (ticketId: string) =>
    api.get(`/tickets/${ticketId}`),
  getEvents: (ticketId: string) =>
    api.get(`/tickets/${ticketId}/events`),
  create: (payload: Record<string, unknown>) =>
    api.post("/tickets", payload),
  update: (ticketId: string, payload: Record<string, unknown>) =>
    api.put(`/tickets/${ticketId}`, payload),
  delete: (ticketId: string) =>
    api.delete(`/tickets/${ticketId}`),
  move: (ticketId: string, payload: { column?: string; status?: string }) =>
    api.put(`/tickets/${ticketId}/move`, payload),
  setLabels: (ticketId: string, label_ids: number[]) =>
    api.put(`/tickets/${ticketId}/labels`, { label_ids }),
  getComments: (ticketId: string) =>
    api.get(`/tickets/${ticketId}/comments`),
  addComment: (ticketId: string, body: string) =>
    api.post(`/tickets/${ticketId}/comments`, { body }),
  updateComment: (ticketId: string, commentId: number, body: string) =>
    api.put(`/tickets/${ticketId}/comments/${commentId}`, { body }),
  deleteComment: (ticketId: string, commentId: number) =>
    api.delete(`/tickets/${ticketId}/comments/${commentId}`),
  getAttachments: (ticketId: string) =>
    api.get(`/tickets/${ticketId}/attachments`),
  uploadAttachment: (ticketId: string, formData: FormData, commentId?: number) =>
    api.post(`/tickets/${ticketId}/attachments`, formData, {
      params: commentId ? { comment_id: commentId } : undefined,
      headers: { "Content-Type": "multipart/form-data" },
    }),
  deleteAttachment: (attachmentId: number) =>
    api.delete(`/attachments/${attachmentId}`),
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

export const actionsApi = {
  apply: (
    recommendationId: number,
    payload: {
      action_type?: string;
      override_priority?: number;
      confirm?: boolean;
      note?: string;
    },
  ) => api.post(`/actions/recommendations/${recommendationId}/apply`, payload),
  get: (actionRunId: number) => api.get(`/actions/${actionRunId}`),
};

export const intelligenceApi = {
  health: () => api.get("/intelligence/health"),
};

export const governanceApi = {
  summary: () => api.get("/governance/summary"),
  card: () => api.get("/governance/card"),
};

export const replayApi = {
  get: (ticketId: string) => api.get(`/replay/${ticketId}`),
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
  listUsers: () => api.get("/auth/users"),
  createUser: (payload: Record<string, unknown>) =>
    api.post("/auth/users", payload),
  updateUser: (username: string, payload: Record<string, unknown>) =>
    api.put(`/auth/users/${username}`, payload),
  deleteUser: (username: string) =>
    api.delete(`/auth/users/${username}`),
  changePassword: (current_password: string, new_password: string) =>
    api.post("/auth/change-password", { current_password, new_password }),
};

export const catalogApi = {
  options: () => api.get("/options"),
  listCategories: () => api.get("/categories"),
  createCategory: (payload: Record<string, unknown>) =>
    api.post("/categories", payload),
  updateCategory: (categoryId: number, payload: Record<string, unknown>) =>
    api.put(`/categories/${categoryId}`, payload),
  deleteCategory: (categoryId: number) =>
    api.delete(`/categories/${categoryId}`),
  listLabels: () => api.get("/labels"),
  createLabel: (payload: Record<string, unknown>) =>
    api.post("/labels", payload),
  deleteLabel: (labelId: number) =>
    api.delete(`/labels/${labelId}`),
  listAssignees: () => api.get("/assignees"),
  createAssignee: (display_name: string) =>
    api.post("/assignees", { display_name }),
  deleteAssignee: (display_name: string) =>
    api.delete("/assignees", { params: { display_name } }),
};
