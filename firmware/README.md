# Firmware

## PoC 빌드 + 업로드

```bash
pio run -e poc -t upload
```

## 시리얼 모니터

```bash
pio device monitor -b 115200
```

## 환경 분기

- `env:poc` - PoC 1주차 단독 모듈 테스트용
- `env:prod` - 본 개발 (8주차 이후 추가 예정)
