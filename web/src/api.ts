// Thin client for the FastAPI backend. The access token from /api/auth/activate is kept in localStorage.
const TOKEN_KEY = "mvai_token";

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode: the session still works until reload */
  }
}

/** Anonymous per-browser id for open demo access, so visitors don't share cases or referrals. */
function visitorId(): string {
  try {
    let id = localStorage.getItem("mvai_visitor");
    if (!id) {
      id = crypto.randomUUID().replace(/-/g, "");
      localStorage.setItem("mvai_visitor", id);
    }
    return id;
  } catch {
    return "";
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Visitor", visitorId());
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let message = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* not JSON */
    }
    if (res.status === 401) window.dispatchEvent(new Event("mvai:unauthorized"));
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown) => ({ body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) => request<T>(path, { method: "POST", ...json(body) }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", ...json(body) }),
  form: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),

  /** Streams the assistant's answer; calls onText with the full text so far. */
  async chat(body: unknown, onText: (text: string) => void): Promise<string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    headers["X-Visitor"] = visitorId();
    const res = await fetch("/api/chat", { method: "POST", headers, body: JSON.stringify(body) });
    if (!res.ok || !res.body) {
      let message = "The assistant could not answer.";
      try {
        message = (await res.json()).detail || message;
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, message);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let text = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      onText(text);
    }
    return text;
  },
};

// ----------------------------------------------------------------------------- shared types
/* eslint-disable @typescript-eslint/no-explicit-any */
export type Report = Record<string, any>;

export interface Licence {
  licence_id: string;
  organisation: string;
  plan: string;
  expires: string | null;
  role: string;
}

export interface Specialist {
  id: string;
  badge: string;
  title: string;
  department: string;
  focus: string;
}

export interface Config {
  licensing: boolean;
  open_access: boolean;
  ai: boolean;
  hospital: string;
  disclaimer: string;
  persistent_appointments: boolean;
  specialists: Specialist[];
  urgency: Record<string, { priority: number; label: string; target: string; description: string }>;
  statuses: Record<string, string>;
}

export interface Sample {
  name: string;
  label: string;
  truth: string;
  tag: string;
  url: string;
}

export interface Case {
  id: string;
  modality: "brain_mri" | "colorectal";
  report: Report;
  images: Record<string, string>;
}

export const pct = (p: number | null | undefined) =>
  p == null ? "—" : p > 0.999 ? ">99.9%" : p < 0.001 ? "<0.1%" : `${(p * 100).toFixed(1)}%`;
