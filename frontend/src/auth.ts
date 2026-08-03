export const AUTH_KEY = "cr_demo_auth";

export function isLoggedIn(): boolean {
  return localStorage.getItem(AUTH_KEY) === "1";
}

export function login(username: string, password: string): boolean {
  const u = username.trim().toUpperCase();
  if (u === "ADMIN" && password === "ADMIN123") {
    localStorage.setItem(AUTH_KEY, "1");
    return true;
  }
  return false;
}

export function logout(): void {
  localStorage.removeItem(AUTH_KEY);
}
