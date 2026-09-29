import { getToken, logout } from "./auth";

/**
 * Empty = same-origin / Vite proxy (default local demo).
 * Set VITE_API_BASE=http://HOST:8000 so another PC talks to a shared backend.
 */
const base = String(import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(extra || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function parseErrorMessage(r: Response): Promise<string> {
  const text = (await r.text()).trim();
  if (!text) {
    if (r.status >= 500) {
      return "Backend unavailable. Start the backend on port 8000, then try again.";
    }
    return `Request failed (${r.status})`;
  }
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: string }).msg) : String(d)))
        .join("; ");
    }
  } catch {
    /* plain text */
  }
  return text;
}

async function handleResponse<T>(r: Response, opts?: { skipAuthRedirect?: boolean }): Promise<T> {
  if (r.status === 401 && !opts?.skipAuthRedirect) {
    logout();
    window.location.href = "/login";
    throw new Error("Session expired. Please log in again.");
  }
  if (!r.ok) {
    throw new Error(await parseErrorMessage(r));
  }
  if (r.status === 204) return undefined as T;
  return r.json();
}

export type UploadResult = {
  filename: string;
  decision: string;
  reason: string;
  sha256: string;
  size_bytes: number;
  original_size_bytes?: number | null;
  max_similarity: number;
  risk_score: number;
  ml_redundant_probability: number;
  content_match_percent?: number;
  compared_to_filename?: string | null;
  compared_to_user?: string | null;
  content_guidance?: string | null;
  toast_message?: string | null;
  policy_threshold_percent?: number;
};

export type DashboardStats = {
  total_upload_attempts: number;
  total_stored_files: number;
  rejected_duplicates: number;
  rejected_redundant: number;
  storage_saved_bytes: number;
  avg_risk_stored: number;
  by_decision: Record<string, number>;
};

export type UploadEvent = {
  id: number;
  original_name: string;
  decision: string;
  size_bytes: number;
  max_similarity: number;
  risk_score: number;
  reason: string;
  created_at: string;
  kind: string;
  user_id?: number;
  username?: string | null;
};

export type UserAccount = {
  id: number;
  username: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: UserAccount;
};

export async function loginApi(
  username: string,
  password: string
): Promise<LoginResponse> {
  const r = await fetch(`${base}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  // Do not redirect on failed login — show a clean error instead
  return handleResponse<LoginResponse>(r, { skipAuthRedirect: true });
}

export async function fetchStats(): Promise<DashboardStats> {
  const r = await fetch(`${base}/api/stats`, { headers: authHeaders() });
  return handleResponse<DashboardStats>(r);
}

export async function fetchMyStats(): Promise<DashboardStats> {
  const r = await fetch(`${base}/api/me/stats`, { headers: authHeaders() });
  return handleResponse<DashboardStats>(r);
}

export async function fetchEvents(userId?: number): Promise<UploadEvent[]> {
  const qs = new URLSearchParams({ limit: "100" });
  if (userId != null) qs.set("user_id", String(userId));
  const r = await fetch(`${base}/api/events?${qs}`, {
    headers: authHeaders(),
  });
  return handleResponse<UploadEvent[]>(r);
}

export async function fetchMyEvents(): Promise<UploadEvent[]> {
  const r = await fetch(`${base}/api/me/events?limit=100`, {
    headers: authHeaders(),
  });
  return handleResponse<UploadEvent[]>(r);
}

export async function fetchMyDuplicates(): Promise<UploadEvent[]> {
  const r = await fetch(`${base}/api/me/duplicates?limit=100`, {
    headers: authHeaders(),
  });
  return handleResponse<UploadEvent[]>(r);
}

export async function uploadFile(
  file: File,
  model?: string
): Promise<UploadResult> {
  const fd = new FormData();
  fd.append("file", file);
  if (model) fd.append("model", model);
  const r = await fetch(`${base}/api/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: fd,
  });
  return handleResponse<UploadResult>(r);
}

export async function fetchUsers(): Promise<UserAccount[]> {
  const r = await fetch(`${base}/api/admin/users`, { headers: authHeaders() });
  return handleResponse<UserAccount[]>(r);
}

export async function createUser(body: {
  username: string;
  password: string;
  role?: string;
}): Promise<UserAccount> {
  const r = await fetch(`${base}/api/admin/users`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleResponse<UserAccount>(r);
}

export async function updateUser(
  id: number,
  body: { is_active?: boolean; password?: string }
): Promise<UserAccount> {
  const r = await fetch(`${base}/api/admin/users/${id}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleResponse<UserAccount>(r);
}

export async function deleteUser(id: number): Promise<void> {
  const r = await fetch(`${base}/api/admin/users/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleResponse<void>(r);
}
