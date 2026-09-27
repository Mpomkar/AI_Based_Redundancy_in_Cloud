import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createUser,
  deleteUser,
  fetchUsers,
  updateUser,
  UserAccount,
} from "../api";
import { getUser, logoutWithToast } from "../auth";
import Toast from "../components/Toast";
import { useToast } from "../hooks/useToast";

export default function UserManagement() {
  const nav = useNavigate();
  const admin = getUser();
  const { toast, toastKind, showToast, clearToast } = useToast();
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"user" | "admin">("user");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    setErr(null);
    const rows = await fetchUsers();
    setUsers(rows);
  }, []);

  useEffect(() => {
    setLoading(true);
    refresh()
      .catch((e) => {
        setErr(String(e));
        showToast(String(e), "error");
      })
      .finally(() => setLoading(false));
  }, [refresh, showToast]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setErr(null);
    try {
      const created = await createUser({
        username: username.trim(),
        password,
        role,
      });
      setUsername("");
      setPassword("");
      setRole("user");
      showToast(
        `User "${created.username}" created successfully (${created.role}).`,
        "success"
      );
      await refresh();
    } catch (e) {
      setErr(String(e));
      showToast(String(e), "error");
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(u: UserAccount) {
    setErr(null);
    try {
      const updated = await updateUser(u.id, { is_active: !u.is_active });
      showToast(
        updated.is_active
          ? `User "${u.username}" activated.`
          : `User "${u.username}" deactivated.`,
        "success"
      );
      await refresh();
    } catch (e) {
      setErr(String(e));
      showToast(String(e), "error");
    }
  }

  async function removeUser(u: UserAccount) {
    if (!window.confirm(`Delete user "${u.username}"? This cannot be undone.`))
      return;
    setErr(null);
    try {
      await deleteUser(u.id);
      showToast(`User "${u.username}" deleted successfully.`, "success");
      await refresh();
    } catch (e) {
      setErr(String(e));
      showToast(String(e), "error");
    }
  }

  return (
    <div className="dash-root">
      <Toast message={toast} kind={toastKind} onClose={clearToast} />
      <header className="dash-header">
        <h1 className="dash-header-title">User Management</h1>
        <div className="dash-header-actions">
          <Link to="/admin" className="dash-nav-link">
            Dashboard
          </Link>
          <span className="dash-user-chip">{admin?.username ?? "Admin"}</span>
          <button
            type="button"
            className="dash-logout"
            onClick={() => {
              logoutWithToast(
                `Goodbye${admin?.username ? `, ${admin.username}` : ""}! You are logged out.`
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

        <section className="user-mgmt-grid">
          <div className="user-form-card">
            <h3 className="sec-title">Create User Account</h3>
            <form onSubmit={onCreate} className="user-form">
              <label className="user-form-field">
                <span>Username</span>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  disabled={creating}
                />
              </label>
              <label className="user-form-field">
                <span>Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  disabled={creating}
                />
              </label>
              <label className="user-form-field">
                <span>Role</span>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as "user" | "admin")}
                  disabled={creating}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </label>
              <button type="submit" className="upload-primary" disabled={creating}>
                {creating ? "Creating…" : "Create User"}
              </button>
            </form>
          </div>

          <div className="dash-table-card user-table-card">
            <div className="table-head">All Users</div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.username}</td>
                      <td>{u.role}</td>
                      <td className={u.is_active ? "st-stored" : "st-rejected"}>
                        {u.is_active ? "Active" : "Inactive"}
                      </td>
                      <td>{new Date(u.created_at).toLocaleString()}</td>
                      <td className="td-action user-actions">
                        <Link
                          to={`/admin?user=${u.id}`}
                          className="btn-secondary"
                          style={{
                            textDecoration: "none",
                            display: "inline-block",
                          }}
                        >
                          View files
                        </Link>
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={u.id === admin?.id}
                          onClick={() => void toggleActive(u)}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                        <button
                          type="button"
                          className="btn-danger"
                          disabled={u.id === admin?.id || u.role === "admin"}
                          onClick={() => void removeUser(u)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!loading && users.length === 0 && (
                <p className="empty-hint">No users found.</p>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
