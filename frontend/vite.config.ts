import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // When VITE_API_BASE is set, the browser calls that host directly (no proxy needed).
  // Proxy remains for default local demo (empty VITE_API_BASE).
  const proxyTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      host: true, // listen on 0.0.0.0 so other PCs can open this UI
      port: 5173,
      proxy: {
        "/api": proxyTarget,
        "/static": proxyTarget,
      },
    },
  };
});
