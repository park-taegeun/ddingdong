# 🎯 Git Convention

본 프로젝트의 모든 commit 메시지는 **한국어**로 작성하며 다음 규칙을 따른다.

## 형식

```
{이모지} {Type}: {한국어 설명}
```

## Type 종류

- 🎉 **Start**: Start New Project [:tada]
- ✨ **Feat**: 새로운 기능을 추가 [:sparkles]
- 🐛 **Fix**: 버그 수정 [:bug]
- 🎨 **Design**: CSS 등 사용자 UI 디자인 변경 [:art]
- ♻️ **Refactor**: 코드 리팩토링 [:recycle]
- 🔧 **Settings**: Changing configuration files [:wrench]
- 🗃️ **Comment**: 필요한 주석 추가 및 변경 [:card_file_box]
- ➕ **Dependency/Plugin**: Add a dependency/plugin [:heavy_plus_sign]
- 📝 **Docs**: 문서 수정 [:memo]
- 🔀 **Merge**: Merge branches [:twisted_rightwards_arrows]
- 🚀 **Deploy**: Deploying stuff [:rocket]
- 🚚 **Rename**: 파일 혹은 폴더명을 수정하거나 옮기는 작업만인 경우 [:truck]
- 🔥 **Remove**: 파일을 삭제하는 작업만 수행한 경우 [:fire]
- ⏪ **Revert**: 전 버전으로 롤백 [:rewind]

## 사용 예시

```
🎉 Start: 프로젝트 초기 monorepo 구조 셋업
✨ Feat: camera_test.cpp 골격 추가 (OV3660 분기 포함)
🐛 Fix: VL53L5CX I2C 주소 오타 수정
🔧 Settings: platformio.ini에 ESP32-S3 board 옵션 추가
➕ Dependency/Plugin: SparkFun_VL53L5CX_Arduino_Library 추가
📝 Docs: decisions.md 카테고리 2 핀 표 갱신
🚚 Rename: src/main.cpp → src/integrated_test.cpp
🔥 Remove: 미사용 wifi_test_v0.cpp 삭제
```

## 작성 원칙

1. **한국어 우선**: 영어 commit 메시지 금지 (Type 키워드는 영어 유지)
2. **이모지 필수**: 한눈에 변경 종류 파악용
3. **간결하게**: 50자 이내 권장
4. **하나의 commit = 하나의 목적**: 여러 Type 섞이면 commit 분리

## 본문(body) 작성 (선택)

긴 설명이 필요하면 제목과 한 줄 띄우고 한국어로 작성:

```
✨ Feat: PoC용 RMS 임계값 측정 함수 추가

조용한 환경 baseline + 도어벨/노크 환경 측정 로직 포함.
임계값은 80% 지점에 자동 산출.
근거: docs/decisions.md 카테고리 3 (음향 트리거).
```

## Claude Code MCP 사용 시

github MCP에 commit 위임할 때 다음을 명시:

- "find-skills로 'git commit convention' skill 탐색 후 사용"
- "commit 메시지는 docs/git-convention.md 규칙 따름 (한국어 + 이모지)"
