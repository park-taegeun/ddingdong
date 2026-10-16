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
  // 사진: demo_up dry · 터널 없이 띄운 dev는 사진 주소가 상대 경로 /captures/<id>라
  // 이 프록시가 없으면 사진 요청이 dev 서버 자신에게 간다(늘 실패). live는 터널
  // 절대 주소라 영향 없음. 서버 mock_enrichment가 내는 mock 사진 경로는 넘기지
  // 않는다(원래 404 = 의도된 동작). demo_up --self-test가 target 문자열과 사진
  // 프록시 키를 대조한다 — 이 파일만 고치면 그쪽이 FAIL로 알린다.
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
      "/captures": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
})
