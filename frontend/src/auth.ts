export const TOKEN_KEY = "cr_auth_token";
export const USER_KEY = "cr_auth_user";

export type AuthUser = {
  id: number;
  username: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
};

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isLoggedIn(): boolean {
  return Boolean(getToken());
}

export function isAdmin(): boolean {
  return getUser()?.role === "admin";
}

export function setSession(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Clear session and queue a toast on the login page. */
export function logoutWithToast(message = "You have been logged out successfully."): void {
  logout();
  // Lazy import avoided — keep key in sync with Toast.tsx FLASH_KEY
  try {
    sessionStorage.setItem(
      "cr_flash_toast",
      JSON.stringify({ message, kind: "info" })
    );
  } catch {
    /* ignore */
  }
}

export function homePathForRole(role: string): string {
  return role === "admin" ? "/admin" : "/portal";
}
