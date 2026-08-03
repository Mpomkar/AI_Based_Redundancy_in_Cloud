const base = "";

async function apiError(response: Response): Promise<Error> {
  const text = (await response.text()).trim();
  if (text) return new Error(text);
  if (response.status >= 500) {
    return new Error(
      "Backend unavailable. Start it: cd backend && .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
    );
  }
  return new Error(`Request failed (${response.status})`);
}

export type UploadResult = {
  filename: string;
  decision: string;
  reason: string;
  sha256: string;
  size_bytes: number;
  max_similarity: number;
  risk_score: number;
  ml_redundant_probability: number;
  content_match_percent?: number;
  compared_to_filename?: string | null;
  content_guidance?: string | null;
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
};

export async function fetchStats(): Promise<DashboardStats> {
  const r = await fetch(`${base}/api/stats`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchEvents(): Promise<UploadEvent[]> {
  const r = await fetch(`${base}/api/events?limit=100`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function uploadFile(
  file: File,
  model?: string
): Promise<UploadResult> {
  const fd = new FormData();
  fd.append("file", file);
  if (model) fd.append("model", model);
  const r = await fetch(`${base}/api/upload`, { method: "POST", body: fd });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t);
  }
  return r.json();
}
