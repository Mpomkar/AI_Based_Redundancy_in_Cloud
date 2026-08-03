import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  DashboardStats,
  UploadEvent,
  UploadResult,
  fetchEvents,
  fetchStats,
  uploadFile,
} from "../api";
import { logout } from "../auth";

const MODELS = [
  "Logistic Regression",
  "Random Forest",
  "HistGradientBoosting",
  "Neural Network (MLP)",
];

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
  if (x.endsWith(".pptx")) return "📊";
  return "📁";
}

function rowAction(ev: UploadEvent): string {
  if (ev.decision === "rejected_duplicate") return "Duplicate";
  if (ev.decision === "rejected_redundant") return "Redundant";
  if (ev.max_similarity >= 0.55 && ev.max_similarity < 0.85) return "Similar";
  if (ev.max_similarity < 0.2) return "Unique";
  return "Normal";
}

export default function Dashboard() {
  const nav = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [events, setEvents] = useState<UploadEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [model, setModel] = useState(MODELS[0]);
  const [lastAnalysis, setLastAnalysis] = useState<UploadResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    const [s, e] = await Promise.all([fetchStats(), fetchEvents()]);
    setStats(s);
    setEvents(e);
  }, []);

  useEffect(() => {
    setLoading(true);
    refresh()
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [refresh]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setUploading(true);
      setErr(null);
      try {
        for (const f of Array.from(files)) {
          const res = await uploadFile(f, model);
          setLastAnalysis(res);
        }
        await refresh();
      } catch (e) {
        setErr(String(e));
      } finally {
        setUploading(false);
      }
    },
    [refresh, model]
  );

  const totalFiles = stats?.total_upload_attempts ?? 0;
  const redundantCount =
    (stats?.rejected_duplicates ?? 0) + (stats?.rejected_redundant ?? 0);
  const efficiency =
    totalFiles > 0 ? Math.round((redundantCount / totalFiles) * 100) : 0;

  const redundantPie = totalFiles
    ? Math.round((redundantCount / totalFiles) * 100)
    : 0;
  const pieData = [
    { name: "Non-Redundant", value: 100 - redundantPie, fill: "#4A90E2" },
    { name: "Redundant", value: redundantPie, fill: "#E74C3C" },
  ];

  let hi = 0,
    med = 0,
    lo = 0;
  for (const ev of events) {
    const r = ev.risk_score;
    if (r >= 66) hi++;
    else if (r >= 34) med++;
    else lo++;
  }
  const nEv = events.length || 1;
  const riskBars = [
    { name: "High", pct: Math.round((hi / nEv) * 100), fill: "#E74C3C" },
    { name: "Medium", pct: Math.round((med / nEv) * 100), fill: "#F39C12" },
    { name: "Low", pct: Math.round((lo / nEv) * 100), fill: "#2ECC71" },
  ];

  const showHighAlert = events.some((e) => e.risk_score >= 70);

  return (
    <div className="dash-root">
      <header className="dash-header">
        <h1 className="dash-header-title">
          AI-Based Cloud Redundancy Prediction System
        </h1>
        <button
          type="button"
          className="dash-logout"
          onClick={() => {
            logout();
            nav("/login", { replace: true });
          }}
        >
          Logout
        </button>
      </header>

      <div className="dash-body">
        {err && <div className="dash-banner-err">{err}</div>}

        <section className="dash-kpi-row">
          <div className="kpi kpi-blue">
            <span className="kpi-icon">📁</span>
            <div>
              <div className="kpi-label">Total Files</div>
              <div className="kpi-value">{loading ? "…" : totalFiles}</div>
            </div>
          </div>
          <div className="kpi kpi-red">
            <span className="kpi-icon">⚠️</span>
            <div>
              <div className="kpi-label">Redundant Files</div>
              <div className="kpi-value">{loading ? "…" : redundantCount}</div>
            </div>
          </div>
          <div className="kpi kpi-green">
            <span className="kpi-icon">☁️</span>
            <div>
              <div className="kpi-label">Storage Saved</div>
              <div className="kpi-value">
                {loading ? "…" : formatBytes(stats?.storage_saved_bytes ?? 0)}
              </div>
            </div>
          </div>
          <div className="kpi kpi-orange">
            <span className="kpi-icon">⚙️</span>
            <div>
              <div className="kpi-label">Efficiency</div>
              <div className="kpi-value">{loading ? "…" : `${efficiency}%`}</div>
            </div>
          </div>
        </section>

        <section className="dash-mid">
          <div className="dash-table-card">
            <div className="table-head">File Status</div>
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
                  {events.slice(0, 12).map((ev) => {
                    const rb = riskBand(ev.risk_score);
                    const stored = ev.decision === "stored";
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
                        <td
                          className={stored ? "st-stored" : "st-rejected"}
                        >
                          {stored ? "Stored" : "Rejected"}
                        </td>
                        <td className="td-action">{rowAction(ev)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!loading && events.length === 0 && (
                <p className="empty-hint">No files yet — upload below.</p>
              )}
            </div>
          </div>

          <aside className="dash-alerts">
            <h3 className="alerts-title">Alerts &amp; Recommendations</h3>
            {showHighAlert && (
              <div className="alert-box alert-warn">
                ⚠️ High Redundancy Risk Detected.
              </div>
            )}
            <div className="alert-box alert-ok">
              ✓ Storage Optimization Suggested.
            </div>
            <ul className="checklist">
              <li>Remove Duplicate Files</li>
              <li>Compress Large Files</li>
              <li>Schedule Cleanup</li>
            </ul>
          </aside>
        </section>

        <section className="dash-charts">
          <div className="chart-card">
            <h3>Redundancy Breakdown</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label
                >
                  {pieData.map((e, i) => (
                    <Cell key={i} fill={e.fill} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-card">
            <h3>Risk Distribution</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={riskBars}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ddd" />
                <XAxis dataKey="name" />
                <YAxis domain={[0, 100]} unit="%" />
                <Tooltip />
                <Bar dataKey="pct" radius={[6, 6, 0, 0]}>
                  {riskBars.map((e, i) => (
                    <Cell key={i} fill={e.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="dash-upload-section">
          <div className="upload-col">
            <h3 className="sec-title">
              <span className="sec-ico">📂</span> File Upload
            </h3>
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

            {lastAnalysis && (
              <div className="donut-wrap">
                <div className="donut-label">
                  {Math.round(lastAnalysis.max_similarity * 100)}%
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={[
                        {
                          name: "match",
                          value: Math.round(lastAnalysis.max_similarity * 100),
                        },
                        {
                          name: "rest",
                          value: Math.max(
                            0,
                            100 - Math.round(lastAnalysis.max_similarity * 100)
                          ),
                        },
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={70}
                      dataKey="value"
                    >
                      <Cell fill="#4A90E2" />
                      <Cell fill="#dfe6e9" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <p className="donut-cap">Similarity vs library</p>
              </div>
            )}
          </div>

          <div className="analysis-card">
            {lastAnalysis ? (
              <>
                <div className="analysis-banner ok">
                  ✓ File processed: {lastAnalysis.filename}
                </div>
                <ul className="analysis-list">
                  <li>
                    <strong>Hash Check:</strong>{" "}
                    {lastAnalysis.decision === "rejected_duplicate"
                      ? "Exact duplicate found"
                      : "No exact duplicate found"}
                  </li>
                  <li>
                    <strong>Content match (best):</strong>{" "}
                    {(lastAnalysis.content_match_percent ??
                      lastAnalysis.max_similarity * 100
                    ).toFixed(1)}
                    %
                    {lastAnalysis.compared_to_filename && (
                      <span className="compared-hint">
                        {" "}
                        vs &quot;{lastAnalysis.compared_to_filename}&quot;
                      </span>
                    )}
                  </li>
                  <li>
                    <strong>Policy threshold:</strong>{" "}
                    {lastAnalysis.policy_threshold_percent ?? "—"}% (reject at or
                    above)
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
                    <strong>Prediction:</strong>{" "}
                    <span
                      className={
                        lastAnalysis.decision === "stored" ? "pred-ok" : "pred-bad"
                      }
                    >
                      {lastAnalysis.decision === "stored"
                        ? "Not Redundant"
                        : "Redundant"}
                    </span>
                  </li>
                  <li>
                    <strong>Action:</strong>{" "}
                    {lastAnalysis.decision === "stored" ? "Stored" : "Not Stored"}
                  </li>
                  {lastAnalysis.decision !== "stored" && (
                    <li>
                      <strong>Storage Saved:</strong>{" "}
                      {formatBytes(lastAnalysis.size_bytes)}
                    </li>
                  )}
                  {lastAnalysis.content_guidance && (
                    <li className="guidance-li">
                      <strong>Guidance:</strong>
                      <pre className="guidance-pre">{lastAnalysis.content_guidance}</pre>
                    </li>
                  )}
                </ul>
                <button
                  type="button"
                  className="view-dash-btn"
                  onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                >
                  View Dashboard
                </button>
              </>
            ) : (
              <p className="analysis-placeholder">
                Upload a file to see hash check, similarity, risk, and prediction.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
