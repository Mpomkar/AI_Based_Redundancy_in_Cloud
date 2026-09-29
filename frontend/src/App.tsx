import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getUser, homePathForRole, isAdmin, isLoggedIn } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import UserPortal from "./pages/UserPortal";
import UserManagement from "./pages/UserManagement";

function Protected({ children }: { children: ReactNode }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />;
}

function AdminRoute({ children }: { children: ReactNode }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  if (!isAdmin()) return <Navigate to="/portal" replace />;
  return children;
}

function UserRoute({ children }: { children: ReactNode }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  // Regular users use portal; admins belong on /admin (global view)
  if (isAdmin()) return <Navigate to="/admin" replace />;
  return children;
}

function RoleHome() {
  const user = getUser();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homePathForRole(user.role)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <Dashboard />
          </AdminRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <AdminRoute>
            <UserManagement />
          </AdminRoute>
        }
      />
      <Route
        path="/portal"
        element={
          <UserRoute>
            <UserPortal />
          </UserRoute>
        }
      />
      <Route
        path="/"
        element={
          <Protected>
            <RoleHome />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
