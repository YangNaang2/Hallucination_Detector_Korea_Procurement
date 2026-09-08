import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 개발 서버(5173)에서 띄울 때 API 요청을 FastAPI(8000)로 넘긴다.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
