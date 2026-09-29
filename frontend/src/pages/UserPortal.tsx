import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchMyDuplicates,
  fetchMyEvents,
  fetchMyStats,
  UploadEvent,
  UploadResult,
  uploadFile,
} from "../api";
import { getUser, logoutWithToast } from "../auth";
import Toast, { toastKindFromDecision } from "../components/Toast";
import { useToast } from "../hooks/useToast";
import {
  UPLOAD_HINT,
  errorMessage,
  validateUploadFileClient,
} from "../uploadValidation";

const MODELS = [
  "Logistic Regression",
  // Keep aligned with admin dashboard — backend uses Logistic Regression only
];

function rowAction(ev: UploadEvent): string {
  if (ev.decision === "rejected_duplicate") return "Duplicate";
  if (ev.decision === "rejected_redundant") return "Redundant";
  if (ev.decision === "stored_shared") return "Shared 0 KB";
  if (ev.max_similarity >= 0.55 && ev.max_similarity < 0.85) return "Similar";
  if (ev.max_similarity < 0.2) return "Unique";
  return "Normal";
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const u = ["KB", "MB", "GB"];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${u[i]}`;
}

function riskBand(r: number): { label: string; cls: string } {
  if (r >= 66) return { label: "High", cls: "risk-high" };
  if (r >= 34) return { label: "Medium", cls: "risk-med" };
  return { label: "Low", cls: "risk-low" };
}

function fileEmoji(name: string): string {
  const x = name.toLowerCase();
  if (x.endsWith(".pdf")) return "📄";
  if (x.match(/\.(jpg|jpeg|png|gif|webp)$/)) return "🖼️";
  if (x.endsWith(".zip")) return "🗜️";
  if (x.endsWith(".docx")) return "📝";
  return "📁";
}

function decisionLabel(decision: string): string {
  if (decision === "rejected_duplicate") return "Exact Duplicate";
  if (decision === "rejected_redundant") return "Near Duplicate";
  if (decision === "stored_shared") return "Stored (0 KB shared)";
  if (decision === "stored") return "Stored";
  return decision;
}

export default function UserPortal() {
  const nav = useNavigate();
  const account = getUser();
  const [stats, setStats] = useState<Awaited<ReturnType<typeof fetchMyStats>> | null>(null);
  const [myEvents, setMyEvents] = useState<UploadEvent[]>([]);
  const [duplicates, setDuplicates] = useState<UploadEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [model, setModel] = useState(MODELS[0]);
  const [lastAnalysis, setLastAnalysis] = useState<UploadResult | null>(null);
  const { toast, toastKind, showToast, clearToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    // User-scoped APIs only — never call admin /api/stats or /api/events
    const [s, e, d] = await Promise.all([
      fetchMyStats(),
      fetchMyEvents(),
      fetchMyDuplicates(),
    ]);
    setStats(s);
    setMyEvents(e);
    setDuplicates(d);
  }, []);

  useEffect(() => {
    setLoading(true);
    refresh()
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        void refresh().catch(() => {});
      }
    };
    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setUploading(true);
      setErr(null);
      try {
        for (const f of Array.from(files)) {
          const clientErr = validateUploadFileClient(f);
          if (clientErr) {
            setErr(clientErr);
            showToast(clientErr, "error");
            continue;
          }
          const res = await uploadFile(f, model);
          setLastAnalysis(res);
          if (res.toast_message) {
            showToast(res.toast_message, toastKindFromDecision(res.decision));
          }
        }
        await refresh();
      } catch (e) {
        const msg = errorMessage(e);
        setErr(msg);
        showToast(msg, "error");
      } finally {
        setUploading(false);
      }
    },
    [refresh, model, showToast]
  );

  const duplicateCount =
    (stats?.rejected_duplicates ?? 0) + (stats?.rejected_redundant ?? 0);

  return (
    <div className="dash-root">
      <Toast message={toast} kind={toastKind} onClose={clearToast} />
      <header className="dash-header">
        <h1 className="dash-header-title">User Portal</h1>
        <div className="dash-header-actions">
          <span className="dash-user-chip">
            {account?.username ?? "User"}
          </span>
          <button
            type="button"
            className="dash-logout"
            onClick={() => {
              logoutWithToast(
                `Goodbye${account?.username ? `, ${account.username}` : ""}! You are logged out.`
              );
              nav("/login", { replace: true });
            }}
          >
            Logout
          </button>
        </div>
      </header>

      <div className="dash-body">
        {err && <div className="dash-banner-err">{err}</div>}

        <section className="dash-kpi-row">
          <div className="kpi kpi-blue">
            <span className="kpi-icon">📁</span>
            <div>
              <div className="kpi-label">My Uploads</div>
              <div className="kpi-value">{loading ? "…" : stats?.total_upload_attempts ?? 0}</div>
            </div>
          </div>
          <div className="kpi kpi-red">
            <span className="kpi-icon">⚠️</span>
            <div>
              <div className="kpi-label">Duplicates Blocked</div>
              <div className="kpi-value">{loading ? "…" : duplicateCount}</div>
            </div>
          </div>
          <div className="kpi kpi-green">
            <span className="kpi-icon">✓</span>
            <div>
              <div className="kpi-label">Stored Files</div>
              <div className="kpi-value">{loading ? "…" : stats?.total_stored_files ?? 0}</div>
            </div>
          </div>
          <div className="kpi kpi-orange">
            <span className="kpi-icon">💾</span>
            <div>
              <div className="kpi-label">Storage Saved</div>
              <div className="kpi-value">
                {loading ? "…" : formatBytes(stats?.storage_saved_bytes ?? 0)}
              </div>
            </div>
          </div>
        </section>

        <section className="dash-table-card" style={{ marginBottom: "1.25rem" }}>
          <div className="table-head">My File Status</div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Similarity</th>
                  <th>Risk Score</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {myEvents.slice(0, 12).map((ev) => {
                  const rb = riskBand(ev.risk_score);
                  const stored =
                    ev.decision === "stored" || ev.decision === "stored_shared";
                  return (
                    <tr key={ev.id}>
                      <td>
                        <span className="fn-icon">{fileEmoji(ev.original_name)}</span>{" "}
                        {ev.original_name}
                      </td>
                      <td>{(ev.max_similarity * 100).toFixed(0)}%</td>
                      <td>
                        <span className={`risk-pill ${rb.cls}`}>
                          {ev.risk_score.toFixed(0)}% ({rb.label})
                        </span>
                      </td>
                      <td className={stored ? "st-stored" : "st-rejected"}>
                        {ev.decision === "stored_shared"
                          ? "Stored 0 KB"
                          : stored
                            ? "Stored"
                            : "Rejected"}
                      </td>
                      <td className="td-action">{rowAction(ev)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!loading && myEvents.length === 0 && (
              <p className="empty-hint">No files yet — upload below.</p>
            )}
          </div>
        </section>

        <section className="dash-upload-section user-portal-grid">
          <div className="upload-col">
            <h3 className="sec-title">
              <span className="sec-ico">📂</span> Upload Files
            </h3>
            <p className="portal-hint">
              You only see your own uploads. Files are checked against your library only — not other users.
              {" "}
              {UPLOAD_HINT}
            </p>
            <label className="model-row">
              <span>Model</span>
              <select
                className="model-select"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={uploading}
              >
                {MODELS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <div
              className={`drop-zone ${dragOver ? "drop-active" : ""}`}
              onDragEnter={(e) => {
                e.preventDefault();
                if (!uploading) setDragOver(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                if (!uploading) setDragOver(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                if (!e.currentTarget.contains(e.relatedTarget as Node))
                  setDragOver(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                if (!uploading) void handleFiles(e.dataTransfer.files);
              }}
              onClick={() => !uploading && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/*"
                multiple
                hidden
                disabled={uploading}
                onChange={async (e) => {
                  await handleFiles(e.target.files);
                  e.target.value = "";
                }}
                onClick={(ev) => ev.stopPropagation()}
              />
              <div className="drop-ico">☁️</div>
              <p className="drop-txt">
                Drag &amp; Drop file here or{" "}
                <span className="linkish">Browse Files</span>
              </p>
              <button
                type="button"
                className="upload-primary"
                disabled={uploading}
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                {uploading ? "Processing…" : "Upload"}
              </button>
            </div>
          </div>

          <div className="analysis-card">
            {lastAnalysis ? (
              <>
                <div className="analysis-banner ok">
                  ✓ File processed: {lastAnalysis.filename}
                </div>
                <ul className="analysis-list">
                  <li>
                    <strong>Result:</strong>{" "}
                    <span
                      className={
                        lastAnalysis.decision === "stored" ||
                        lastAnalysis.decision === "stored_shared"
                          ? "pred-ok"
                          : "pred-bad"
                      }
                    >
                      {decisionLabel(lastAnalysis.decision)}
                    </span>
                  </li>
                  <li>
                    <strong>Stored size:</strong>{" "}
                    {formatBytes(lastAnalysis.size_bytes)}
                    {lastAnalysis.decision === "stored_shared" &&
                      lastAnalysis.original_size_bytes != null && (
                        <span className="compared-hint">
                          {" "}
                          (original {formatBytes(lastAnalysis.original_size_bytes)})
                        </span>
                      )}
                  </li>
                  <li>
                    <strong>Similarity:</strong>{" "}
                    {(lastAnalysis.content_match_percent ??
                      lastAnalysis.max_similarity * 100
                    ).toFixed(1)}
                    %
                    {lastAnalysis.compared_to_user && (
                      <span className="compared-hint">
                        {" "}
                        (also on account "{lastAnalysis.compared_to_user}")
                      </span>
                    )}
                  </li>
                  <li>
                    <strong>Risk Score:</strong>{" "}
                    <span
                      className={`risk-pill ${riskBand(lastAnalysis.risk_score).cls}`}
                    >
                      {lastAnalysis.risk_score.toFixed(0)}% (
                      {riskBand(lastAnalysis.risk_score).label})
                    </span>
                  </li>
                  <li>
                    <strong>Reason:</strong> {lastAnalysis.reason}
                  </li>
                </ul>
              </>
            ) : (
              <p className="analysis-placeholder">
                Upload a file to see whether it is unique or a duplicate of something you already uploaded.
              </p>
            )}
          </div>
        </section>

        <section className="dash-table-card">
          <div className="table-head">Duplicate Files Detected</div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Type</th>
                  <th>Similarity</th>
                  <th>Risk</th>
                  <th>Status</th>
                  <th>Reason</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {duplicates.map((ev) => {
                  const rb = riskBand(ev.risk_score);
                  return (
                    <tr key={ev.id}>
                      <td>
                        <span className="fn-icon">{fileEmoji(ev.original_name)}</span>{" "}
                        {ev.original_name}
                      </td>
                      <td>{ev.kind}</td>
                      <td>{(ev.max_similarity * 100).toFixed(0)}%</td>
                      <td>
                        <span className={`risk-pill ${rb.cls}`}>
                          {ev.risk_score.toFixed(0)}%
                        </span>
                      </td>
                      <td className="st-rejected">{decisionLabel(ev.decision)}</td>
                      <td>{ev.reason}</td>
                      <td>{new Date(ev.created_at).toLocaleString()}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!loading && duplicates.length === 0 && (
              <p className="empty-hint">No duplicate files detected yet.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
