import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the browser talks to Vite, which forwards /api to FastAPI (no CORS needed).
// Production: set VITE_API_URL to the deployed backend origin (CORS_ORIGINS on the backend must include the frontend origin).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target: process.env.VITE_PROXY_TARGET || "http://localhost:8000", changeOrigin: true } } },
});
