import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { isLoggedIn, login } from "../auth";

export default function Login() {
  const nav = useNavigate();
  useEffect(() => {
    if (isLoggedIn()) nav("/", { replace: true });
  }, [nav]);
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [err, setErr] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    if (login(user, pass)) nav("/", { replace: true });
    else setErr("Invalid username or password.");
  }

  return (
    <div className="login-page">
      <div className="login-bg-pattern" aria-hidden />
      <div className="login-card">
        <h1 className="login-title">Admin Login</h1>
        <form onSubmit={onSubmit}>
          <label className="login-field">
            <span className="login-label">Username</span>
            <div className="login-input-wrap">
              <span className="login-icon">👤</span>
              <input
                className="login-input"
                placeholder="admin"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                autoComplete="username"
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
              />
            </div>
          </label>
          {err && <p className="login-err">{err}</p>}
          <button type="submit" className="login-btn">
            Login
          </button>
        </form>
        <button type="button" className="login-forgot">
          Forgot Password?
        </button>
      </div>
    </div>
  );
}
