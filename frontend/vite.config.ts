import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      // Local dev convenience: proxy API calls so the browser only ever
      // talks to http://localhost:5173 (same-origin). This keeps the
      // session cookie as SameSite=Lax during local development — no
      // cross-site cookie rules to fight with. Only used when VITE_API_URL
      // is left empty; see frontend/.env.example.
      proxy: {
        "/api": {
          target: env.VITE_PROXY_TARGET || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
