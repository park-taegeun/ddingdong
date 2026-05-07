# 띵동 (DdingDong)

청각장애인용 현관 부착형 소리 분류 알림 시스템 - 졸업작품

> **운영 정책**: 본 repo는 졸업작품 시연 전까지 **private**으로 운영하며, 시연 종료 후 **public** 전환 예정.

---

## 22주 일정 요약

| 주차 | 기간 | 단계 | 핵심 작업 |
|------|------|------|-----------|
| 사전 | 5/7~5/17 | 준비 | 펌웨어 골격 / 외부 계정 / 부품 검수 |
| 1 | 5/18~5/24 | PoC 1주차 | 단독 모듈 검증 + RMS 임계값 측정 |
| 2~7 | 5/25~7/5 | 본 개발 (펌웨어) | 통합 펌웨어 / VL53L5CX 검증 |
| 8~10 | 7/6~7/26 | 본 개발 (ML) | YAMNet Fine-tuning / 데이터 수집 |
| 11~14 | 7/27~8/23 | 본 개발 (서버) | Flask + EC2 + STT + 카카오톡 |
| 15~18 | 8/24~9/20 | 본 개발 (대시보드) | React + 접근성 UI |
| 19~22 | 9/21~10/18 | 통합 + 시연 | 통합 테스트 / 시연 / 회고 |

> 상세 일정·결정은 `docs/decisions.md` 참조.

---

## 기술 스택

- **펌웨어**: ESP32-S3 (XIAO Sense Pre-Soldered, OV3660) + INMP441 + VL53L5CX
- **ML**: YAMNet Fine-tuning (raw waveform 16kHz mono) + FastDTW SP/DTW (초인종 개인 등록)
- **서버**: AWS EC2 t3.small + Nginx + Gunicorn + Flask + SQLite
- **STT**: Naver Clova Speech (CSR)
- **알림**: 카카오톡 '나에게 보내기' (memo API)
- **대시보드**: Vite + React + shadcn/ui (Tailwind)

---

## 폴더 구조

```
ddingdong/
├── firmware/        # ESP32-S3 펌웨어 (PlatformIO)
├── server/          # Flask 서버 (11주차 진입 시 채움)
├── dashboard/       # React 대시보드 (15주차 진입 시 채움)
├── ml/              # YAMNet 학습 코드 (8주차 진입 시 채움)
├── docs/
│   ├── decisions.md         # 🔴 SSoT (모든 결정의 단일 진실 원천)
│   ├── decisions-log.md     # 🔴 결정 변경 이력
│   ├── git-convention.md    # 🔴 한국어 + 이모지 commit 규칙
│   ├── poc-week1-plan.md
│   ├── research/            # 호환성/사양 검증 리서치
│   └── hardware/            # 결선도 / 부품 사양
├── .env.example
└── README.md
```

---

> 🔴 **코드 작업 전 필독**
> 모든 코드/펌웨어 작업은 `docs/decisions.md` 최신본을 git pull로 받은 후 시작.
> 결정 변경 시 본 채팅방(전략) → decisions.md 갱신 → 채팅방 2(구현) 순서.
> 채팅방 2에서 구현 중 새 이슈 발견 시 본 채팅방으로 escalate.

> 🔴 **Commit 메시지 규칙**
> 모든 commit은 한국어 + 이모지 컨벤션을 따른다.
> 상세: `docs/git-convention.md`
> 형식: `{이모지} {Type}: {한국어 설명}`
> 예: `✨ Feat: camera_test.cpp 골격 추가`
