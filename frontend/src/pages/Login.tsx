import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginApi } from "../api";
import { getUser, homePathForRole, isLoggedIn, setSession } from "../auth";
import Toast, { setFlashToast } from "../components/Toast";
import { useToast } from "../hooks/useToast";

export default function Login() {
  const nav = useNavigate();
  const { toast, toastKind, showToast, clearToast } = useToast();
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const account = getUser();
    if (isLoggedIn() && account) {
      nav(homePathForRole(account.role), { replace: true });
    }
  }, [nav]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const res = await loginApi(user.trim(), pass);
      setSession(res.access_token, res.user);
      setFlashToast(
        `Welcome, ${res.user.username}! Signed in as ${res.user.role}.`,
        "success"
      );
      nav(homePathForRole(res.user.role), { replace: true });
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Invalid username or password.";
      setErr(msg);
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <Toast message={toast} kind={toastKind} onClose={clearToast} />
      <div className="login-bg-pattern" aria-hidden />
      <div className="login-card">
        <h1 className="login-title">Sign In</h1>
        <p className="login-subtitle">
          Admin and user accounts use the same login page.
        </p>
        <form onSubmit={onSubmit}>
          <label className="login-field">
            <span className="login-label">Username</span>
            <div className="login-input-wrap">
              <span className="login-icon">👤</span>
              <input
                className="login-input"
                placeholder="admin or your username"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                autoComplete="username"
                disabled={loading}
              />
            </div>
          </label>
          <label className="login-field">
            <span className="login-label">Password</span>
            <div className="login-input-wrap">
              <span className="login-icon">🔒</span>
              <input
                className="login-input"
                type="password"
                placeholder="••••••••"
                value={pass}
                onChange={(e) => setPass(e.target.value)}
                autoComplete="current-password"
                disabled={loading}
              />
            </div>
          </label>
          {err && <p className="login-err">{err}</p>}
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? "Signing in…" : "Login"}
          </button>
        </form>
        <p className="login-hint">
          Admin: <strong>admin</strong> / <strong>ADMIN123</strong>
          <br />
          Demo user: <strong>user</strong> / <strong>USER123</strong>
        </p>
      </div>
    </div>
  );
}
