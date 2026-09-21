import { clsx, type ClassValue } from "clsx"
import { extendTailwindMerge } from "tailwind-merge"

// index.css 의 `@theme` 블록에 정의된 커스텀 글자 크기 토큰(--text-*)을 tailwind-merge 에 등록한다.
// ① index.css 에서 --text-* 를 추가·삭제하면 이 목록도 같이 고쳐야 한다(자동 가드 없음).
// ② 등록하지 않으면 twMerge 가 `text-caption` 류를 색 그룹(text-<색>)으로 오분류해,
//    cn("… text-caption …", "text-success") 처럼 색과 겹치는 순간 크기 클래스가 사라진다 —
//    코드에는 있는데 화면에는 안 먹는다(8.7(c)).
// ③ 기본 'font-size' 그룹에 넣지 않고 별도 그룹을 쓴다. 그 그룹은 leading 과도 충돌해
//    (conflictingClassGroups 의 'font-size': ['leading']) `leading-none … text-h3` 에서
//    leading-none 을 지우는데, 우리 토큰은 line-height 를 함께 내보내지 않으므로 거짓 충돌이다.
//    stock 크기 클래스(text-sm/lg/xs …)와는 양방향으로 묶어 "뒤에 온 쪽이 이긴다"를 유지한다.
// ④ PR #57 의 `text-(length:--text-*)` 우회는 이 설정과 무관하게 그대로 동작한다.
const TEXT_SIZE_TOKENS = ["display", "h1", "h2", "h3", "body", "caption"]

// 인스턴스는 모듈 레벨에서 1회만 만든다 — 호출마다 만들면 내부 LRU 캐시가 무력화된다.
const twMerge = extendTailwindMerge<"text-size-token">({
  extend: {
    classGroups: { "text-size-token": [{ text: TEXT_SIZE_TOKENS }] },
    conflictingClassGroups: {
      "text-size-token": ["font-size"],
      "font-size": ["text-size-token"],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
