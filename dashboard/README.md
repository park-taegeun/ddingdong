# 띵동 대시보드 (React)

띵동 서버의 알림 · 통계 · 초인종 소리 등록 · 시스템 상태를 보여 주는 웹 대시보드. Vite + React + TypeScript + Tailwind.
서버를 3초마다 폴링한다(`src/lib/constants.ts` `POLLING_INTERVAL_MS`). 응답 스키마는 `src/types/`가 서버와 1:1로 맞춘다.

## scripts (`dashboard/`에서)

```bash
npm run dev       # vite 개발 서버 :5173 · /api → localhost:5000 프록시
npm run build     # tsc -b && vite build
npm run lint      # eslint .
npm run preview   # 빌드 결과 미리 보기
npm run ssr-nc    # negative control 하네스 — 소스를 일시 변형 → SSR 렌더 → 텍스트 단언 → 복원
```

## 환경변수

| 이름 | 용도 |
|---|---|
| `VITE_API_BASE_URL` | API 주소. 비우면 상대경로(`/api/v1/...`)로 요청한다 |
| `VITE_DASHBOARD_TOKEN` | 서버의 대시보드용 인증 토큰(기기용 토큰과 따로 쓴다) |

클라이언트 코드는 상대경로 `/api/v1/...`로 요청해야 dev 프록시 · 터널 양쪽에서 동작한다.

## 검증 순서

1. `npm run lint` · `npm run build` 통과
2. 커밋
3. `npm run ssr-nc` 통과 — 테스트 러너가 없어서 이 하네스가 대신한다. 단언 축은 텍스트 라벨뿐이다(색 · 아이콘 · 레이아웃은 검사하지 않는다).

## 원칙

- 신규 런타임 의존성 0 — 아이콘 · 애니메이션 · 테스트 하네스는 이미 설치된 것(lucide-react · CSS · react-dom · vite)으로 해결한다.
- 결정 · 근거의 단일 출처는 [`docs/decisions.md`](../docs/decisions.md)(카테고리 8 = 대시보드)이다.
