# `other` 네거티브 후보 선별 (E3 1단계)

학습 분포 밖 입력(목소리 · 잡음 · 인터폰 전자음)이 `fire_alarm` 으로 수렴하는 문제
(33.6(a)(f)(g))를 4번째 클래스 `other` 로 흡수하기로 했다(D4). 이 패키지는 그 중
**E3 = 네거티브 출처는 로컬 FSD50K 덤프 우선** 의 첫 단계로, 로컬 dev 덤프에서
**후보 목록(CSV)만** 만든다.

오디오를 복사·변환·3초 조각내기 하지 않는다(재학습 소관). 데이터셋과 메타데이터는
둘 다 읽기 전용으로만 연다.

## 실행

```bash
python -m ml.curation.select_negatives \
  --dev-csv        "~/ML 학습 데이터/fsd50k_meta/FSD50K.ground_truth/dev.csv" \
  --vocabulary-csv "~/ML 학습 데이터/fsd50k_meta/FSD50K.ground_truth/vocabulary.csv" \
  --clips-info     "~/ML 학습 데이터/fsd50k_meta/FSD50K.metadata/dev_clips_info_FSD50K.json" \
  --pp-pnp         "~/ML 학습 데이터/fsd50k_meta/FSD50K.metadata/pp_pnp_ratings_FSD50K.json" \
  --audio-root     "~/ML 학습 데이터/ddingdong_dataset/00_source_raw/fsd50k/dev_audio/FSD50K.dev_audio" \
  --positive-clips "~/ML 학습 데이터/ddingdong_dataset/01_clips" \
  --out-dir        "~/ddingdong-측정결과/2026-09-21/negatives"
```

경로에 기본값은 없다 — 빠뜨리면 즉시 실패한다. 산출(`candidates.csv` ·
`summary.md` · `listen_sample.csv`)은 **repo 밖** `--out-dir` 에만 쓴다.

라벨 메타데이터(ground truth · vocabulary · clip info · pp_pnp)는 Zenodo record
4060432 의 `FSD50K.ground_truth.zip` · `FSD50K.metadata.zip` 이며, 로컬
`00_source_raw/fsd50k` 덤프에는 오디오만 있어 데이터셋 **밖** 에 따로 둔다.
오디오 루트와 메타데이터 경로는 서로 다른 인자다.

## 선별 규칙

**제외**

| # | 규칙 |
| --- | --- |
| ① | target 계열 라벨 — `Doorbell` · `Knock` · `Siren`, 그리고 「미분화 `Alarm`」 |
| ② | `01_clips` 양성에 이미 쓴 FSD50K 원본 ID (순수 숫자 stem, 조각 suffix 제거 후) |
| ③ | 길이 < `config.MIN_DURATION_SEC`, 그리고 0바이트·헤더 손상으로 열리지 않는 wav |

**포함** — ⓐ 음성·대화 / ⓑ 방송·음악 / ⓒ 생활음 / ⓓ hard negative.
배정은 `taxonomy.py` 의 200 라벨 전건 수기 표가 SSoT 다.

**보류** — target 과 음향적으로 인접하지만 라벨만으로 못 가르는 것.
후보에서 빼되 집계에는 남긴다: `Tap` · `Chime` · `Wind_chime` · `Bicycle_bell` ·
`Church_bell` · `Glockenspiel` · `Marimba_and_xylophone` · `Mallet_percussion` ·
`Thump_and_thud` · `Wood` · 미분화 `Door` · 미분화 `Bell`.

## 라벨 배정 근거

### 번짐(smearing)과 부모 라벨

dev.csv 라벨은 온톨로지 부모 방향으로 번져 있다. 로컬에 `ontology.json` 이 없어
**dev.csv 동시출현 구조로 관계를 추정**했다(근거유형 = 논증). 어떤 라벨 X 가 붙은
클립이 **100% 예외 없이** 라벨 Y 도 함께 갖는다면 Y 를 X 의 상위로 본다.

실측 결과:

- `Doorbell`(107) ⊂ `Alarm`(1,280) ∩ `Door`(1,056) ∩ `Domestic_sounds…`(4,711)
- `Knock`(270) ⊂ `Door`(1,056) ⊂ `Domestic_sounds…`
- `Siren`(77) ⊂ `Alarm`
- `Alarm` 의 하위: `Telephone`(520) · `Vehicle_horn…`(115) · `Doorbell`(107) ·
  `Ringtone`(97) · `Siren`(77) · `Bicycle_bell`(73)
- `Door` 의 하위: `Slam`(351) · `Knock`(270) · `Sliding_door`(196) · `Doorbell`(107)

🔴 **부모는 제외 기준으로 쓰지 않는다.** `Door` 로 제외하면 `Slam` · `Sliding_door`
같은 문 형제가, `Alarm` 으로 제외하면 `Telephone` · `Ringtone` 같은 경보 형제가
통째로 사라진다. 그런데 바로 그 `Telephone` · `Ringtone` 이 33.6(a)(f)(g) 의 실패
모드(인터폰 전자음 → `fire_alarm`)를 겨냥한 핵심 hard negative 다.

대신 **미분화** 만 잡는다 — 부모만 붙고 하위 라벨이 하나도 없는 클립. 미분화
`Alarm` 은 어떤 경보인지 갈리지 않으므로 `fire_alarm` 과 구별할 수 없어 **제외**,
미분화 `Door` · `Bell` 은 노크·딩동일 수 있어 **보류** 다.

### 음색 인접 보류 5건 (2026-09-21 보정)

온톨로지상 target 의 자식이 아니지만 **음색이 target 과 인접해** 라벨만으로는
`other` 라고 단정할 수 없는 5건을 보류로 옮겼다. `Chime` · `Tap` 을 보류로 둔 것과
같은 근거이며, 잘못 넣으면 E4 의 target recall 을 직접 깎는다.

| 라벨 | 이전 | 인접 target | 근거 |
| --- | --- | --- | --- |
| `Glockenspiel` | ⓑ | doorbell | 초인종 "딩동" 차임과 금속 타건 음색이 인접 |
| `Marimba_and_xylophone` | ⓑ | doorbell | 〃 (건반 타악 배음 구조) |
| `Mallet_percussion` | ⓑ | doorbell | 위 둘의 상위 계열 — 같이 옮기지 않으면 새어 든다 |
| `Thump_and_thud` | ⓓ | knock | 문 두드림 = 둔탁한 타격음 그 자체 |
| `Wood` | ⓒ | knock | 노크 대상이 나무 문 — 나무 둔탁음과 겹친다 |

`Speech_synthesizer` 는 **무변경**(ⓐ) — 인터폰 전자 음성 쪽이라 오히려 필요한
hard negative 일 수 있어 청취 검수 뒤에 판단한다.

### 라벨 불완전 대응 (PP 우선)

FSD50K 공식 설명상 dev 라벨은 "correct but could be occasionally incomplete" 다.
`pp_pnp_ratings` 로 선택 라벨이 **PP(주 음원)** 인 클립을 먼저 고른다
(1.0 = PP / 0.5 = PNP / 0 = NP / -1 = unsure 는 평균에서 제외). 후보 CSV 의
`rating` · `rating_value` 열과 요약의 PP/PNP 비율이 그 결과다.

### 선택 라벨과 규모

한 클립에 여러 라벨이 붙으므로 대표 하나를 고른다 — ⓓ > ⓐ > ⓑ > ⓒ 우선,
같은 범주면 **희소한 쪽**(번짐으로 올라붙은 상위 노드가 아니라 잎에 가까운 쪽).
다중 라벨은 제외 규칙에 **하나라도** 걸리면 제외한다.

규모 시작값은 1,100 클립. 라벨당 상한은 「모든 라벨에 같은 상한을 두고 목표를 넘지
않는 최대값」으로 잡고, 상한에 못 미치는 희소 라벨 때문에 남은 자리만 결정적으로
돌려준다. 어느 한 라벨이 후보를 독식하지 않게 하는 게 목적이다.

선택은 **sha256 기반 결정적** 이다(내장 `hash()` 는 프로세스마다 salt 가 달라져
쓰지 않는다). 같은 입력이면 항상 같은 CSV 가 나온다.

## 검증

```bash
python -m ml.curation.tests.test_select_negatives
```

가짜 메타데이터로 T1~T5(제외 ①②③ · 결정성 · 산출 형식)를 돌리고, 이어서
네거티브 컨트롤 NC-1~NC-3 으로 **규칙을 망가뜨리면 해당 테스트가 실제로 깨지는지**
확인한 뒤 `finally` 로 복원하고 전건 재통과를 다시 본다.
