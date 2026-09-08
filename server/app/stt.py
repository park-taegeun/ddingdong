"""Naver CSR(CLOVA Speech Recognition) STT 클라이언트 (카테고리 7 STT / 30.9).

`server/` 의 STT 호출 코드는 본 모듈 이전까지 **0줄**이었다(30.9 "왕복 실증 ≠ 서버
배선"). 2026-09-05 에 실증된 것은 **왕복**이고, 그 왕복을 서버 요청 경로에 얹는 것이
이 모듈이다 — 두 사실은 분리해 읽어야 한다.

HTTP 는 표준 라이브러리 urllib 로 한다. 근거 = kakao.py 와 동형(repo 에 서드파티
HTTP 클라이언트 사용처 0건, requests/httpx 미설치). 신규 의존성 없음.

env 게이트: NCP_CLIENT_ID / NCP_CLIENT_SECRET 이 **둘 다** 설정돼야 real 모드.
미설정 = 호출하지 않고 기존 mock 자막 유지 — model_serving.is_real_mode()
(DDINGDONG_MODEL_PATH 게이트, 카테고리 6.2)와 같은 패턴이다. 신규 스위치를 발명하지
않았다(학습 16).

★ 재시도 없음. 근거 2:
  ① CSR 은 **15초 단위 과금**이다(2026-09-05 콘솔 usage=15 실측, 30.9 — 4.1초 호출
     1건이 15초로 계상됐다). 소프트 한도는 일 500초 / 월 5,000초이고 "설정 적용 중
     수 초 내 초과 호출 가능"이라 하드 스톱도 아니다. 즉 재시도 1회는 인식률이 아니라
     **과금과 한도 소진만 정확히 2배**로 만든다.
  ② 카테고리 7 "1차 알림 재시도 없음" 규약과 동형. 2차 카카오 발송의 "1회 재시도"는
     같은 바이트를 다시 **보내는** 비용이 왕복뿐이라 성립했지만, STT 는 재호출 자체가
     과금 단위를 하나 더 소비한다 — 비용 구조가 다르므로 같은 정책을 물려받지 않는다.
  ★ 백오프 대기 상수를 두지 않는다. 재시도가 없으므로 참조처가 0인 죽은 상수가 된다.

★ 로그 위생 (카테고리 21 시크릿 위생 연장): Client ID/Secret 값과 **인식 결과 전문**을
  로그에 남기지 않는다. transcript 는 길이만 남긴다 — 방문자 발화는 개인정보이고,
  1차 알림 경로가 이미 "에러 본문을 싣지 않는다"(kakao.py)로 같은 선을 그었다.
"""

import io
import json
import urllib.error
import urllib.parse
import urllib.request
import wave

from flask import current_app

from .constants import (
    STT_CLIENT_ID_HEADER,
    STT_CLIENT_SECRET_HEADER,
    STT_CSR_LANG,
    STT_CSR_URL,
    STT_HTTP_TIMEOUT_SECONDS,
)

# server/inference 는 frozen sibling 패키지(카테고리 6.2) — import 만. 오디오 포맷의
# SSoT 를 여기에 다시 적지 않는다(중복 신설 금지).
from inference.constants import BYTES_PER_SAMPLE, SAMPLE_RATE

# WAV 채널 수. 카테고리 4/33.2 "raw waveform 16kHz **mono**" — inference.constants 에
# 채널 상수는 없고(모노가 전제라 변수가 아니다), 여기서 값을 발명하지 않기 위해
# 근거만 각인하고 리터럴로 둔다.
_WAV_CHANNELS = 1


class SttAuthError(RuntimeError):
    """자격증명 계층 실패 — 미설정 / 401 / 403.

    kakao.py 의 KakaoTokenError 와 같은 자리다. 분류 기준도 같다: **다시 쏴도 결과가
    바뀌지 않는 실패**를 별도 계층으로 올려, 호출부가 "네트워크가 흔들렸다"와
    "자격증명이 틀렸다"를 로그에서 구분할 수 있게 한다.
    """


class SttRequestError(RuntimeError):
    """그 외 API/네트워크/응답 실패 — 타임아웃, 5xx, 401·403 아닌 HTTP 오류, 파싱 실패.

    kakao.py 의 KakaoSendError 와 같은 자리. 다만 kakao 와 달리 **재시도 대상이
    아니다**(위 모듈 docstring 재시도 근거 ①). 계층을 나눈 이유는 재시도 분기가 아니라
    로그·회귀에서 원인을 가르기 위함이다.
    """


def is_real_mode():
    """NCP 자격증명이 둘 다 설정됐는가. 아니면 mock 자막 유지(호출 자체를 하지 않는다).

    model_serving.is_real_mode() 동형. 한쪽만 설정된 상태를 real 로 보지 않는 이유 =
    그 상태로 호출하면 반드시 401 을 받아 과금 없는 실패 왕복만 태우기 때문이다.
    """
    return bool(current_app.config.get("NCP_CLIENT_ID")) and bool(
        current_app.config.get("NCP_CLIENT_SECRET")
    )


def wav_from_pcm16(pcm_bytes):
    """16kHz mono 16bit raw PCM → WAV 컨테이너(44바이트 RIFF 헤더 + 원본 바이트).

    ★ 근거: 2026-09-05 CSR 왕복 실측(30.9)은 **WAV 로만** 수행됐다(16kHz mono 16bit
      PCM WAV 131,756 B → `{"text": ...}`, 왕복 0.892초). raw PCM 직송은 이 repo 에서
      한 번도 검증된 적이 없다 — 미검증 경로를 새로 만드는 대신, 실증된 형식에
      맞춰 준다. 판정 방법 = raw PCM 직송을 쓰고 싶어지면 먼저 실 CSR 로 1회 호출해
      같은 인식 결과가 나오는지 확인하고, 그 실측을 30.9 에 등재한 뒤에 바꾼다.

    헤더 필드(ChunkSize / Subchunk2Size / ByteRate / BlockAlign)는 전부 입력 길이에서
    산출한다 — 하드코딩하면 다른 길이의 클립에서 조용히 틀린 헤더를 만든다.
    구현은 표준 라이브러리 `wave` 에 맡긴다(직접 struct 로 조립하지 않는 이유 =
    필드 산출을 손으로 다시 구현하는 것이 곧 버그 표면이다). `wave` 는 close 시점에
    실제 기록된 프레임 수로 헤더를 되쓰므로 산출 규칙이 코드 밖에서 보장된다.
    """
    if len(pcm_bytes) % (BYTES_PER_SAMPLE * _WAV_CHANNELS) != 0:
        # 프레임 경계에 맞지 않는 입력. wave 는 남는 바이트를 조용히 헤더에서 누락시켜
        # "선언 길이 ≠ 실제 데이터"인 파일을 만든다 — 조용한 손상 대신 시끄럽게 거절.
        # (/enrich 경로는 decode_pcm16 이 이미 400 으로 거르지만, 이 함수는 단독으로도
        #  안전해야 한다.)
        raise ValueError(f"PCM 길이가 프레임 경계에 맞지 않습니다: {len(pcm_bytes)} bytes")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(_WAV_CHANNELS)
        w.setsampwidth(BYTES_PER_SAMPLE)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


def build_request(wav_bytes, client_id, client_secret):
    """CSR 요청 조립(순수 — 네트워크 접촉 없음). 값 SSoT = 30.9 왕복 실측.

    lang 은 쿼리스트링, 자격증명은 헤더, 본문은 WAV 바이트 그대로다.
    """
    url = f"{STT_CSR_URL}?{urllib.parse.urlencode({'lang': STT_CSR_LANG})}"
    return urllib.request.Request(
        url,
        data=wav_bytes,
        headers={
            STT_CLIENT_ID_HEADER: client_id,
            STT_CLIENT_SECRET_HEADER: client_secret,
            "Content-Type": "application/octet-stream",
        },
        method="POST",
    )


def parse_transcript(body):
    """CSR 응답 바이트 → 인식 문자열(순수). 실측 응답 형태 = `{"text": "..."}` (30.9).

    빈 문자열/공백만 있는 결과는 그대로 ""(빈 문자열)로 돌려준다 — "자막 없음"으로
    접는 판단은 호출부(routes._caption_from_stt)의 몫이고, 그 접기는 이미 A-2 에서
    ④런타임 검증된 경로다(7.6). 여기서 두 번 접으면 판단 지점이 둘로 갈린다.
    """
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:  # JSONDecodeError / UnicodeDecodeError
        raise SttRequestError(f"CSR 응답 파싱 실패: {type(exc).__name__}") from exc
    text = payload.get("text")
    if text is None:
        # 200 인데 text 키가 없다 = 계약 위반. 조용히 "자막 없음"으로 흡수하면 API
        # 스펙 변경이 무음으로 지나간다(카테고리 20: 부재와 실패를 가른다).
        raise SttRequestError("CSR 응답에 text 필드가 없습니다.")
    return str(text).strip()


def transcribe(pcm_bytes):
    """단일 진입점 — raw PCM 1개를 CSR 로 **정확히 1회** 보내고 인식 문자열을 돌려준다.

    반환: 인식 문자열(빈 문자열일 수 있다).
    예외: SttAuthError(자격증명 미설정/401/403) / SttRequestError(그 외).
      ★ 두 예외 모두 호출부에서 **자막 부재로 흡수**된다(7.6(e) "자막 없음 ≠ 실패").
        STT 실패를 enrich_status="failed" 로 올리면 안 된다 — 그 값은 7.6(d) 에서
        **자막 발송 실패**를 뜻하고, 사진은 정상 발송된 상태이기 때문이다.
    """
    client_id = current_app.config.get("NCP_CLIENT_ID") or ""
    client_secret = current_app.config.get("NCP_CLIENT_SECRET") or ""
    if not client_id or not client_secret:
        # 값이 아니라 "미설정"만 말한다(키 이름조차 값과 함께 남기지 않는다).
        raise SttAuthError("NCP 자격증명 미설정 — CSR 호출 불가")

    try:
        wav_bytes = wav_from_pcm16(pcm_bytes)
    except ValueError as exc:
        raise SttRequestError(f"WAV 합성 실패: {exc}") from exc

    req = build_request(wav_bytes, client_id, client_secret)
    try:
        with urllib.request.urlopen(req, timeout=STT_HTTP_TIMEOUT_SECONDS) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise SttAuthError(f"CSR 인증 거부: HTTP {exc.code}") from exc
        # 에러 본문을 싣지 않는다 — 요청 파라미터 에코 가능성 배제(kakao.py 동형).
        raise SttRequestError(f"CSR 호출 실패: HTTP {exc.code}") from exc
    except Exception as exc:  # URLError/timeout — 원인 타입만 남긴다
        raise SttRequestError(f"CSR 호출 실패: {type(exc).__name__}") from exc

    transcript = parse_transcript(body)
    # 전문 금지 — 길이만. (성공 여부는 이 로그가 남았다는 사실 자체가 말한다.)
    current_app.logger.info(
        "stt csr ok: wav_bytes=%d transcript_len=%d", len(wav_bytes), len(transcript)
    )
    return transcript
