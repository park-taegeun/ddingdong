"""/detect ToF 메타 4종 수신·검증 (카테고리 6.2 G10 wire 확장).

본 모듈의 범위 = **수신측 wire 계층**. ToF 판정은 하지 않는다.

★ 서버가 tof_presence 를 재판정하지 않는 이유 (근거유형 = 논증, 실측 근거 위):
  `tof_presence` 는 디바이스가 Stage A 디바운스(확정 상태와 다른 raw 판정이 연속
  3프레임이어야 전환, 9.2(e))와 Stage B-2 latch(75프레임 = 5초, 9.4(b))를 거쳐
  확정한 값이다. 둘 다 15Hz 프레임 이력이 있어야 성립하는 **시간축 판정**이라
  단발 POST 가 실어 온 스냅샷 한 장으로는 원리적으로 재구성할 수 없다. 서버가
  near_count 로 임계값 8(9.2(d))을 다시 계산하면 디바이스가 확정한 presence 와
  다른 값이 나온다 — 9.2(b) 실측이 그 반례다(전환 직후 near 13→9 하락에도
  디바운스로 DETECTED 유지. 스냅샷만 보면 9 는 8 이상이라 우연히 같은 답이지만,
  near 7 로 한 프레임 더 내려간 순간 서버는 NONE, 디바이스는 DETECTED 가 된다).
  → 게이트 입력은 `tof_presence` 단독. 나머지 3필드는 **증거·표시용 telemetry** 로만
    쓰고 통과 여부를 재계산하지 않는다.

상태 3종 (하류에서 구분 가능해야 한다 — 부재를 '통과'로 위장하지 않는다):
  "absent"  = 4필드 전부 부재 → 게이트 미적용, 현행 동작 보존(fail-open).
              2026-09-03 A-1 end-to-end 완주 경로(7.5)가 ToF 없이 ④런타임을 통과한
              유일한 동작 경로다. 부재를 400 으로 막으면 그 검증분이 회귀한다.
  "present" = tof_presence 파싱 성공 → 게이트 적용.
  "invalid" = 필드가 왔는데 tof_presence 를 읽을 수 없음 → 게이트 미적용 + 사유 기록.

★ 이탈값을 400 으로 거절하지 않는 이유 (근거유형 = 논증): 통합 펌웨어의 표기 버그
  하나가 1차 알림 체인 전체를 죽이는 쪽이, 쓰레기 값을 받아 두고 기록에 남기는 쪽보다
  시연 리스크가 크다. 대신 "조용히 받는" 것도 막는다 — 이탈 필드는 값을 버리고
  (None) `invalid_fields` 와 reason 문자열에 남겨 응답·DB·로그 세 곳에서 보이게 한다.

★ telemetry 이탈이 게이트를 끄지 않는 이유 (근거유형 = 논증): near_count 하나가
  깨졌다고 게이트를 미적용으로 돌리면, presence=false(사람 없음)로 거절될 요청이
  telemetry 를 망가뜨리는 것만으로 통과한다. 게이트 상태는 tof_presence 만 좌우한다.
"""

from .constants import (
    TOF_CENTER_MM_FIELD,
    TOF_MOTION_AGGREGATE_TOTAL,
    TOF_MOTION_NDET_FIELD,
    TOF_NEAR_COUNT_FIELD,
    TOF_PRESENCE_FIELD,
    TOF_ZONE_TOTAL,
)

# 파싱 대상 4종. 이 순서가 reason 문자열의 telemetry 표기 순서이기도 하다.
TOF_FORM_FIELDS = (
    TOF_PRESENCE_FIELD,
    TOF_NEAR_COUNT_FIELD,
    TOF_CENTER_MM_FIELD,
    TOF_MOTION_NDET_FIELD,
)

# multipart 는 전부 문자열로 온다 — "false"/"0"/"" 가 파이썬 truthiness 로 True 가
# 되지 않도록 명시 허용표로만 판정한다. 허용 표기를 좁게 잡는 이유: 송신측이 우리
# 펌웨어라 표기가 하나로 고정돼 있고, 넓게 받으면 오배선("False" 오타, "presence"
# 같은 문자열)이 조용히 참으로 흡수된다. 표에 없는 값(빈 문자열 포함) = 이탈.
_TRUE_TOKENS = frozenset(("true", "1"))
_FALSE_TOKENS = frozenset(("false", "0"))

# 이탈 원문을 reason/DB 로 그대로 흘리지 않기 위한 상한. 대시보드가 이 문자열을
# 렌더하므로 임의 길이·제어문자를 통과시키지 않는다(진단에 필요한 만큼만 남긴다).
_RAW_ECHO_LIMIT = 16


def _parse_bool(raw):
    """허용표 대조 불리언. 표 밖(빈 문자열 포함) → None = 이탈."""
    token = raw.strip().lower()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return None


def _parse_int(raw, maximum):
    """0 이상 정수 파싱. maximum 이 None 이면 상한 검사 없음. 이탈 → None."""
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    if maximum is not None and value > maximum:
        return None
    return value


def absent_meta():
    """ToF 필드가 하나도 실리지 않은 상태의 메타(매 호출 새 dict).

    ToF 를 모르는 호출부(구 시그니처 3인자 호출·기존 회귀 케이스)가 만나는 기본값이
    바로 이 상태다 — 즉 "모르면 게이트 미적용"이 기본이고, 통과가 기본이 아니다.
    """
    return {
        "state": "absent",
        "presence": None,
        "near_count": None,
        "center_mm": None,
        "motion_ndet": None,
        "invalid_fields": (),
    }


def parse_tof_meta(form):
    """multipart form → ToF 메타 dict (순수 함수, form 은 .get 만 요구).

    반환 키:
      state         "absent" | "present" | "invalid"  (게이트 입력의 상태)
      presence      bool | None                        (게이트 값. None = 게이트 미적용)
      near_count    int | None                         (telemetry, 이탈·부재 시 None)
      center_mm     int | None
      motion_ndet   int | None
      invalid_fields tuple[str, ...]                   (이탈로 버려진 필드명 + 원문 일부)
    """
    raw = {name: form.get(name) for name in TOF_FORM_FIELDS}
    if all(value is None for value in raw.values()):
        return absent_meta()

    invalid = []

    def _reject(name, raw_value):
        # 원문은 진단용으로만, 길이·공백을 정리해 남긴다.
        echo = " ".join(str(raw_value).split())[:_RAW_ECHO_LIMIT]
        invalid.append(f"{name}={echo!r}")

    presence_raw = raw[TOF_PRESENCE_FIELD]
    if presence_raw is None:
        # 일부 필드만 온 상태 = 오배선. 게이트 입력이 없으므로 invalid 로 둔다
        # (부재와 같은 fail-open 동작을 하되 사유를 다르게 남긴다).
        presence = None
        invalid.append(f"{TOF_PRESENCE_FIELD}=<missing>")
    else:
        presence = _parse_bool(presence_raw)
        if presence is None:
            _reject(TOF_PRESENCE_FIELD, presence_raw)

    values = {}
    for name, maximum in (
        (TOF_NEAR_COUNT_FIELD, TOF_ZONE_TOTAL),
        # center_mm 상한 없음: decisions.md 에 거리 상한 실측이 없다(9.2(c) 곡선의
        # 최대 관측치 2953mm 는 "그날 그 자리의 관측값"이지 센서 구조 상한이 아니다).
        # 근거 없는 상한을 여기서 창작하면 그것이 곧 실측 없는 판정(카테고리 20 위반)이라
        # 음수만 거른다. ★ 재조정 방법: 유효 거리 상한이 실측으로 등재되면 그 값을
        # constants.py 에 근거와 함께 신설하고 이 자리에 넘긴다.
        (TOF_CENTER_MM_FIELD, None),
        (TOF_MOTION_NDET_FIELD, TOF_MOTION_AGGREGATE_TOTAL),
    ):
        field_raw = raw[name]
        if field_raw is None:
            values[name] = None
            continue
        parsed = _parse_int(field_raw, maximum)
        if parsed is None:
            _reject(name, field_raw)
        values[name] = parsed

    return {
        # telemetry 가 깨져도 게이트 상태는 presence 만 좌우한다(상단 주석 3번째 ★).
        "state": "present" if presence is not None else "invalid",
        "presence": presence,
        "near_count": values[TOF_NEAR_COUNT_FIELD],
        "center_mm": values[TOF_CENTER_MM_FIELD],
        "motion_ndet": values[TOF_MOTION_NDET_FIELD],
        "invalid_fields": tuple(invalid),
    }


def telemetry_summary(meta):
    """증거용 telemetry 요약. 부재 필드는 n/a, 이탈 필드는 invalid 로 표기.

    9.3(b)/9.4(d) 로그 필드 표기(near=13/64, ndet=1/16, center=1015mm)를 그대로 따른다
    — 펌웨어 시리얼 로그와 서버 기록을 같은 어휘로 대조할 수 있게 하기 위함이다.
    """
    if meta["state"] == "absent":
        return ""

    invalid_names = {entry.split("=", 1)[0] for entry in meta["invalid_fields"]}

    def _cell(name, value, suffix):
        if name in invalid_names:
            return "invalid"
        if value is None:
            return "n/a"
        return f"{value}{suffix}"

    # presence 는 불리언이라 "13/64" 같은 수치 표기를 쓰지 않는다(파싱 성공 시 true/false,
    # 실패·부재 시 _cell 의 invalid/n/a 표기를 그대로 따른다).
    if meta["presence"] is None:
        presence = _cell(TOF_PRESENCE_FIELD, None, "")
    else:
        presence = "true" if meta["presence"] else "false"

    return " ".join(
        (
            f"presence={presence}",
            f"near={_cell(TOF_NEAR_COUNT_FIELD, meta['near_count'], f'/{TOF_ZONE_TOTAL}')}",
            f"center={_cell(TOF_CENTER_MM_FIELD, meta['center_mm'], 'mm')}",
            f"ndet={_cell(TOF_MOTION_NDET_FIELD, meta['motion_ndet'], f'/{TOF_MOTION_AGGREGATE_TOTAL}')}",
        )
    )


def evaluate_gate(meta):
    """ToF 게이트 결과 (applied, passed, reason). 클래스별 우회 판단은 호출부 소관.

    - absent  → (False, None, "tof_absent")           게이트 미적용(현행 보존)
    - invalid → (False, None, "tof_invalid(...)")     게이트 미적용 + 이탈 사유
    - present → (True, presence, telemetry 요약)      게이트 적용

    ★ "통과(True, True, ...)"와 "미적용(False, None, ...)"이 applied/passed/reason
      세 값 모두에서 갈린다 — 이 구분 가능성이 부재를 통과로 위장하지 않는다는
      불변식이며, 회귀 스위트가 이를 고정한다.
    """
    state = meta["state"]
    if state == "absent":
        return False, None, "tof_absent"
    if state == "invalid":
        return False, None, f"tof_invalid({', '.join(meta['invalid_fields'])})"
    reason = telemetry_summary(meta)
    if meta["invalid_fields"]:
        # 게이트는 유효(presence 정상)하되 telemetry 일부가 깨진 상태 — 판정은 그대로
        # 내리고 깨진 필드를 사유에 남긴다.
        reason = f"{reason} [invalid: {', '.join(meta['invalid_fields'])}]"
    return True, bool(meta["presence"]), reason
