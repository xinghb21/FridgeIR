import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 默认通过开发服务器把 /api、/health 代理到后端，前端用同源相对路径请求，绕开 CORS。
// 若后端在另一台机器，改 BACKEND 或在 .env 里设 VITE_API_BASE_URL 直连。
const BACKEND = process.env.VITE_BACKEND ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/health": { target: BACKEND, changeOrigin: true },
    },
  },
});
