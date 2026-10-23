import { api, type Schemas } from "./client";

type Detail = Schemas["ApplicationDetail"];

export const Api = {
  demoProfiles: () => api<Schemas["DemoProfile"][]>("GET", "/auth/demo-profiles"),
  login: (login: string) => api<Schemas["Token"]>("POST", "/auth/demo-login", { login }),
  me: () => api<Schemas["User"]>("GET", "/me"),

  products: () => api<Schemas["Product"][]>("GET", "/products"),
  recommend: (body: Schemas["RecommendRequest"]) =>
    api<Schemas["Recommendation"][]>("POST", "/products/recommend", body),

  applications: () => api<Schemas["ApplicationSummary"][]>("GET", "/applications"),
  createApplication: (body: Schemas["ApplicationCreate"]) =>
    api<Detail>("POST", "/applications", body),
  application: (id: number) => api<Detail>("GET", `/applications/${id}`),
  updateApplication: (id: number, body: Schemas["ApplicationPatch"]) =>
    api<Detail>("PATCH", `/applications/${id}`, body),
  submit: (id: number) => api<Detail>("POST", `/applications/${id}/submit`),
  cancel: (id: number) => api<Detail>("POST", `/applications/${id}/cancel`),
  infoResponse: (id: number, body: Schemas["InfoResponse"]) =>
    api<Detail>("POST", `/applications/${id}/info-response`, body),
  acceptOffer: (id: number) => api<Detail>("POST", `/applications/${id}/offer/accept`),
  declineOffer: (id: number) => api<Detail>("POST", `/applications/${id}/offer/decline`),
  requestSignCode: (id: number) =>
    api<Schemas["SignCode"]>("POST", `/applications/${id}/sign/request-code`),
  confirmSign: (id: number, code: string) =>
    api<Detail>("POST", `/applications/${id}/sign/confirm`, { code }),
  events: (id: number) => api<Schemas["Event"][]>("GET", `/applications/${id}/events`),

  notifications: () => api<Schemas["NotificationList"]>("GET", "/notifications"),
  readNotification: (id: number) =>
    api<Schemas["Notification"]>("POST", `/notifications/${id}/read`),

  analystQueue: (status?: string) =>
    api<Schemas["QueueItem"][]>(
      "GET",
      `/analyst/applications${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  analystCard: (id: number) => api<Schemas["AnalystCard"]>("GET", `/analyst/applications/${id}`),
  analystDecision: (id: number, body: Schemas["AnalystDecision"]) =>
    api<Schemas["AnalystCard"]>("POST", `/analyst/applications/${id}/decision`, body),
};
