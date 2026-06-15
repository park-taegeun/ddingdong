import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // ── dev 전용 프록시 ────────────────────────────────────────────────
  // flask-cors 미설치(server/ 수정 금지) → 브라우저에서 5173→5000 직접 호출 시
  // CORS 차단. dev 서버가 /api 요청을 같은 origin처럼 받아 Flask로 포워딩해 우회.
  // 클라이언트는 반드시 상대경로(/api/v1/...)로 호출해야 이 프록시를 탄다.
  // ⚠️ dev 전용: 11주차 EC2 배포 시 Nginx 동일 origin 서빙 또는 백엔드 CORS 별도 필요.
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
})
