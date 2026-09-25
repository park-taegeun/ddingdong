#!/usr/bin/env python3
"""녹음 전용 수신기 — 보드 `env:enrich_uplink`의 1차·2차 오디오를 WAV로 저장한다 (카톡·STT·DB 0).

**성격 = 배관(plumbing)**. 제품 서버(`server/app`)의 `/api/v1/detect` · `/api/v1/enrich` 두 경로만
흉내 내어, 보드가 보내는 PCM을 직접녹음 파일로 남긴다. 판정·임계값·제품 상태 어휘를 새로 만들지 않는다.
- 배경: 직접녹음(노크·초인종)을 폰이 아니라 보드 INMP441 경로로 받는다 — 서비스 때와 같은
  마이크·게인·ToF 조건(decisions.md 5.2(e) 「직접 녹음이 채우는 것은 개체 구분 … INMP441 채널 특성」).
  USB 시리얼 스트리밍은 6.3(j) 「시리얼 절단 정량화」(21.1% 손상)로 기각됐다.
- 펌웨어 0줄: 보드는 지금 펌웨어 그대로다. 's' 한 번 = ① /detect 로 누르기 직전 2.048초(65,536 B)
  ② 응답의 enrich_status 가 "pending" 이면 /enrich 로 누른 뒤 5.120초(163,840 B) + 사진 1장.
  이 수신기는 /detect 에 항상 "pending" 을 돌려줘 2차를 끌어낸다(보드 게이트 = enrich_wire.h
  enrichGateFromDetectBody). 서버 어휘 "pending"/"skipped" 를 **그대로** 쓴다.
- `server/app` 을 import 하지 않는다 — import 하는 순간 app/config.py 가 load_dotenv(server/.env)
  를 실행한다. 계약 상수는 아래에 **복제**하고 `--self-test` 가 원본 파일을 **텍스트로** 읽어 대조한다.

저장 규칙
- 파일명 = direct_{label}_{unit}_{take:02d}.wav (33.12 D3 · ml/pipeline/config.py source_key:
  끝의 _{테이크} 를 떼면 유닛이 그룹 키). pre/ = 1차 2.048초, post/ = 2차 5.120초. 16 kHz mono int16.
- 테이크 번호는 /detect 가 정상 크기일 때만 배정한다. 시작 시 out-dir 의 기존 파일에서 이어 매긴다.
  기존 파일은 절대 덮지 않는다(배타 생성 — 같은 이름이 있으면 저장 거부 + 로그).
- 사진은 바이트 수만 기록하고 디스크에 쓰지 않는다. Authorization 은 있음/없음만 기록한다.
- 계약과 다른 입력(크기·필드 누락·짝 없음)은 저장하지 않고 로그 + manifest.csv status 로 남긴다.
  status 어휘는 이 도구 전용 로그 값이며 제품 enrich_status(7.6(d) 종결 3종)와 무관하다.

--------------------------------------------------------------------------------
학부생 녹음 절차
--------------------------------------------------------------------------------
0) 전제: 보드 secrets.h 의 SPIKE_SERVER_HOST · SPIKE_SERVER_PORT 가 이 노트북 IP · --port 와 같아야
   한다(보드 펌웨어가 쓰는 값. 이 도구는 secrets.h 를 읽지 않는다 — 다르면 학부생 로컬에서 맞춘다).
1) 제품 서버 종료 확인 — 빈 출력이어야 한다:
     lsof -nP -iTCP:5000 -sTCP:LISTEN
2) 노트북 IP 확인:  ipconfig getifaddr en0
3) 자기검증(수 초, 포트를 열지 않는다):
     cd "<repo>/server"
     venv/bin/python3 tools/record_receiver.py --self-test
4) 기동(out-dir 는 repo 밖. 예 = 노크, 유닛 a):
     venv/bin/python3 tools/record_receiver.py --out-dir "$HOME/ddingdong-측정결과/$(date +%F)/direct_rec" \
         --label knock --unit a --port 5000
5) 보드 시리얼 모니터에서 's' → 5초 안에 소리. 보드 로그 `[e2] gate=pending` 뒤 `[e2] e http=201` 이면
   post 저장 완료. 수신기 로그의 take 번호를 확인한다.
6) 보드 세션 상한 = 2차 12건(ENRICH_SESSION_MAX_EVENTS). 12회마다 보드 물리 리셋 버튼.
   상한 뒤의 's' 는 pre 만 저장되고 post 가 없다(manifest 에 pre_saved 만 남음).
"""

import argparse
import csv
import json
import os
import re
import sys
import wave
from array import array
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── 계약 상수 (복제) ────────────────────────────────────────────────────────────
# ⚠️ 동기화 필요: 아래 값은 원본 파일의 복제다. 원본이 바뀌면 여기도 바꿔야 한다.
#    `--self-test` 의 [상수 대조] 가 원본을 텍스트로 읽어 불일치를 FAIL 로 드러낸다.
DETECT_AUDIO_BYTES = 65_536    # firmware/include/uplink_common.h static_assert(UPLINK_AUDIO_BYTES == 65536)
ENRICH_AUDIO_BYTES = 163_840   # firmware/include/enrich_wire.h ENRICH_AUDIO_BUFFERS(80) × 1024 × 2
SAMPLE_RATE = 16_000           # enrich_wire.h ENRICH_AUDIO_SAMPLE_RATE · server/inference/constants.py
RESP_MAX_BYTES = 767           # uplink_common.h UPLINK_RESP_BUF_BYTES(768) − NUL. 넘치면 보드가 잘린 채 파싱 실패
# 보드가 보낼 수 있는 최대 바디 = uplink_common.h UPLINK_ENRICH_BODY_BYTES (새 상한 발명 아님)
MAX_BODY_BYTES = ENRICH_AUDIO_BYTES + 512_000 + 1_024
FIELD_CRID = "client_request_id"   # uplink_common.cpp appendField · enrich_wire.h enrichBuildMultipart
FIELD_AUDIO = "audio"              # UPLINK_AUDIO_FIELD · ENRICH_AUDIO_FIELD · server AUDIO_FILE_FIELD
FIELD_IMAGE = "image"              # ENRICH_IMAGE_FIELD · server IMAGE_FILE_FIELD
TOF_FIELDS = ("tof_presence", "tof_near_count", "tof_center_mm", "tof_motion_ndet")  # server TOF_*_FIELD

LABELS = ("doorbell", "knock")
# 영문·숫자만. 밑줄 금지 — source_key 가 끝의 _숫자를 테이크로 떼어낸다(D3).
# 대문자 허용 = 기존 컨벤션(decisions.md 5.2 예 direct_doorbell_A_01 · PR #69 테스트 유닛 A/B).
UNIT_RE = re.compile(r"^[A-Za-z0-9]+$")

MANIFEST_COLS = ["endpoint", "take", "client_request_id", "received_at",
                 "pre_bytes", "post_bytes", "pre_peak", "post_peak", "pre_clip", "post_clip",
                 *TOF_FIELDS, "image_bytes", "auth", "status"]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def pcm_stats(data):
    """(peak, clip) — peak = |샘플| 최대, clip = ±32767 / −32768 샘플 수."""
    s = array("h", data)
    if sys.byteorder == "big":
        s.byteswap()  # 보드 PCM 은 little-endian
    peak = max((abs(v) for v in s), default=0)
    clip = sum(1 for v in s if v in (32767, -32768))
    return peak, clip


def validate_out_dir(raw):
    out = Path(raw).expanduser().resolve()
    if out == REPO_ROOT or out.is_relative_to(REPO_ROOT):
        sys.exit(f"--out-dir 가 repo 안이다({out}) — 오디오 커밋 방지를 위해 거부. repo 밖 경로를 준다.")
    return out


def take_name(label, unit, take):
    return f"direct_{label}_{unit}_{take:02d}.wav"


def next_take(out, label, unit):
    """out/pre · out/post 의 기존 파일에서 (label, unit)의 다음 번호. 없으면 1."""
    pat = re.compile(rf"^direct_{label}_([A-Za-z0-9]+)_(\d+)\.wav$")
    takes = []
    for sub in ("pre", "post"):
        for p in (out / sub).glob(f"direct_{label}_*.wav"):
            m = pat.match(p.name)
            if not m:
                continue
            if m.group(1) != unit and m.group(1).lower() == unit.lower():
                # macOS 기본 파일시스템은 대소문자를 구분하지 않아 a_01 과 A_01 이 같은 파일이다.
                sys.exit(f"유닛 '{unit}' 과 대소문자만 다른 기존 유닛 '{m.group(1)}' 이 있다({p}) — 같은 표기를 쓴다.")
            if m.group(1) == unit:
                takes.append(int(m.group(2)))
    return max(takes, default=0) + 1


def write_wav_exclusive(path, pcm):
    """배타 생성 — 같은 이름이 있으면 FileExistsError(덮어쓰기 0)."""
    with open(path, "xb") as f, wave.open(f, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)


def create_app(out, label, unit):
    from flask import Flask, Response, request

    for sub in ("pre", "post"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.csv"
    state = {"next": next_take(out, label, unit), "pending": {}}  # pending: client_request_id → take

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

    def record(endpoint, status, **kw):
        row = {c: "" for c in MANIFEST_COLS}
        row.update(endpoint=endpoint, status=status, received_at=datetime.now().isoformat(timespec="seconds"),
                   auth="있음" if request.headers.get("Authorization") else "없음", **kw)
        new = not manifest.exists()
        with open(manifest, "a", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
            if new:
                wr.writeheader()
            wr.writerow(row)
            f.flush()
            os.fsync(f.fileno())

    def reply(code, body):
        text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        return Response(text, status=code, mimetype="application/json")

    def detect_reply(code, enrich_status, **extra):
        # 보드는 "enrich_status" 를 계층 무관 strstr 로 찾는다 — 제품 to_dict 와 같은 하위 중첩으로 둔다.
        return reply(code, {"predicted_class": "record_only",
                            "notification_status": {"enrich_status": enrich_status}, **extra})

    @app.post("/api/v1/detect")
    def detect():
        crid = request.form.get(FIELD_CRID, "")
        f = request.files.get(FIELD_AUDIO)
        tof = {k: request.form[k] for k in TOF_FIELDS if k in request.form}
        pcm = f.read() if f else b""
        if not crid or f is None:
            log(f"/detect 거부: 필드 누락(client_request_id={'있음' if crid else '없음'}, audio={'있음' if f else '없음'})")
            record("detect", "rejected_missing_field", client_request_id=crid, pre_bytes=len(pcm), **tof)
            return detect_reply(400, "skipped")
        if len(pcm) != DETECT_AUDIO_BYTES:
            log(f"/detect 거부: audio {len(pcm)} B ≠ {DETECT_AUDIO_BYTES} B — 저장 안 함 id={crid}")
            record("detect", "rejected_size", client_request_id=crid, pre_bytes=len(pcm), **tof)
            return detect_reply(400, "skipped")
        if crid in state["pending"]:
            log(f"/detect 거부: 이미 받은 client_request_id={crid}")
            record("detect", "rejected_duplicate_id", client_request_id=crid, pre_bytes=len(pcm), **tof)
            return detect_reply(409, "skipped")
        take = state["next"]
        path = out / "pre" / take_name(label, unit, take)
        try:
            write_wav_exclusive(path, pcm)
        except FileExistsError:
            log(f"/detect 거부: {path.name} 이미 있음 — 덮어쓰지 않는다")
            record("detect", "rejected_exists", take=take, client_request_id=crid, pre_bytes=len(pcm), **tof)
            return detect_reply(409, "skipped")
        state["next"] = take + 1
        state["pending"][crid] = take
        peak, clip = pcm_stats(pcm)
        log(f"take {take:02d} pre 저장 peak={peak} clip={clip} tof={tof or '없음'} id={crid}")
        record("detect", "pre_saved", take=take, client_request_id=crid, pre_bytes=len(pcm),
               pre_peak=peak, pre_clip=clip, **tof)
        return detect_reply(200, "pending", take=take)

    @app.post("/api/v1/enrich")
    def enrich():
        crid = request.form.get(FIELD_CRID, "")
        fa, fi = request.files.get(FIELD_AUDIO), request.files.get(FIELD_IMAGE)
        pcm = fa.read() if fa else b""
        image_bytes = len(fi.read()) if fi else ""  # 크기만 — 사진은 디스크에 쓰지 않는다
        take = state["pending"].pop(crid, None)
        if take is None:
            log(f"/enrich orphan: 짝 없는 client_request_id={crid or '(없음)'} — 저장 안 함")
            record("enrich", "orphan", client_request_id=crid, post_bytes=len(pcm), image_bytes=image_bytes)
            return reply(404, {"error": "orphan"})
        if fa is None or fi is None:
            log(f"/enrich 거부: take {take:02d} 필드 누락(audio={'있음' if fa else '없음'}, image={'있음' if fi else '없음'})")
            record("enrich", "rejected_missing_field", take=take, client_request_id=crid,
                   post_bytes=len(pcm), image_bytes=image_bytes)
            return reply(400, {"error": "missing_field"})
        if len(pcm) != ENRICH_AUDIO_BYTES:
            log(f"/enrich 거부: take {take:02d} audio {len(pcm)} B ≠ {ENRICH_AUDIO_BYTES} B — 저장 안 함")
            record("enrich", "rejected_size", take=take, client_request_id=crid,
                   post_bytes=len(pcm), image_bytes=image_bytes)
            return reply(400, {"error": "size"})
        path = out / "post" / take_name(label, unit, take)
        try:
            write_wav_exclusive(path, pcm)
        except FileExistsError:
            log(f"/enrich 거부: {path.name} 이미 있음 — 덮어쓰지 않는다")
            record("enrich", "rejected_exists", take=take, client_request_id=crid,
                   post_bytes=len(pcm), image_bytes=image_bytes)
            return reply(409, {"error": "exists"})
        peak, clip = pcm_stats(pcm)
        log(f"take {take:02d} post 저장 peak={peak} clip={clip} image={image_bytes} B")
        record("enrich", "post_saved", take=take, client_request_id=crid, post_bytes=len(pcm),
               post_peak=peak, post_clip=clip, image_bytes=image_bytes)
        return reply(201, {"take": take})

    @app.errorhandler(413)
    def too_large(_e):
        log(f"{request.path} 거부: 바디가 {MAX_BODY_BYTES} B 초과 — 저장 안 함")
        return reply(413, {"error": "too_large"})

    app.config["RECORD_STATE"] = state  # 자기검증용 노출
    return app


# ── 자기검증 (gate_axis_sweep.py --self-test 선례: 파일 내 함수 + _check PASS/FAIL 줄) ──

def _check(name, passed, detail):
    print(f"  [{'PASS' if passed else 'FAIL'}] {name:<30} {detail}")
    return passed


def board_peek(body, key):
    """enrich_wire.h enrichPeekJson 의 파이썬 이식 — 보드와 같은 방식으로 값을 읽는다."""
    pat = f'"{key}":'
    i = body.find(pat)
    if i < 0:
        return None
    p = i + len(pat)
    while p < len(body) and body[p] == " ":
        p += 1
    quoted = p < len(body) and body[p] == '"'
    p += quoted
    out = ""
    while p < len(body) and len(out) < 15:  # char v[16]
        if (body[p] == '"') if quoted else (body[p] in ",} "):
            break
        out += body[p]
        p += 1
    return out or None


def board_multipart(boundary, fields, files):
    """펌웨어와 같은 바이트열 — form field 먼저, 파일 파트(filename 동봉) 뒤."""
    b = b""
    for k, v in fields:
        b += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, fname, ctype, data in files:
        b += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\n'
              f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n"
    return b + f"--{boundary}--\r\n".encode()


def constant_checks():
    """원본 파일을 텍스트로 읽어 복제 상수와 대조한다(import 금지 — app 은 import 시 .env 를 읽는다)."""
    def grab(rel, pattern):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        found = re.findall(pattern, text)
        return found[0] if len(found) == 1 else f"<{len(found)}건 매치>"

    uh, ew, uc = "firmware/include/uplink_common.h", "firmware/include/enrich_wire.h", "firmware/src/uplink_common.cpp"
    sc, ic = "server/app/constants.py", "server/inference/constants.py"
    bufs, dma = grab(ew, r"ENRICH_AUDIO_BUFFERS\s*=\s*(\d+);"), grab(ew, r"ENRICH_AUDIO_DMA_BUF_LEN\s*=\s*(\d+);")
    enrich_bytes = int(bufs) * int(dma) * 2 if bufs.isdigit() and dma.isdigit() else None
    rows = [
        ("detect 오디오 바이트", grab(uh, r"static_assert\(UPLINK_AUDIO_BYTES == (\d+)"), str(DETECT_AUDIO_BYTES)),
        ("enrich 오디오 바이트", str(enrich_bytes), str(ENRICH_AUDIO_BYTES)),
        ("샘플레이트(보드)", grab(ew, r"ENRICH_AUDIO_SAMPLE_RATE\s*=\s*(\d+);"), str(SAMPLE_RATE)),
        ("샘플레이트(서버)", grab(ic, r"SAMPLE_RATE: int = (\d+)"), str(SAMPLE_RATE)),
        ("PCM dtype(서버)", grab(ic, r'PCM_DTYPE: str = "([^"]+)"'), "<i2"),
        ("응답 버퍼 − 1", str(int(grab(uh, r"UPLINK_RESP_BUF_BYTES = (\d+);")) - 1), str(RESP_MAX_BYTES)),
        ("image 상한(보드)", grab(ew, r"ENRICH_SERVER_IMAGE_MAX_BYTES = (\d+);"), str(MAX_BODY_BYTES - ENRICH_AUDIO_BYTES - 1_024)),
        ("여유폭(보드)", grab(uh, r"UPLINK_MULTIPART_OVERHEAD_BYTES = (\d+);"), "1024"),
        ("audio 필드(1차)", grab(uh, r'UPLINK_AUDIO_FIELD\s*= "(\w+)"'), FIELD_AUDIO),
        ("audio 필드(2차)", grab(ew, r'ENRICH_AUDIO_FIELD\s*= "(\w+)"'), FIELD_AUDIO),
        ("image 필드(2차)", grab(ew, r'ENRICH_IMAGE_FIELD\s*= "(\w+)"'), FIELD_IMAGE),
        ("audio 필드(서버)", grab(sc, r'AUDIO_FILE_FIELD = "(\w+)"'), FIELD_AUDIO),
        ("image 필드(서버)", grab(sc, r'IMAGE_FILE_FIELD = "(\w+)"'), FIELD_IMAGE),
        ("crid 필드(1차)", grab(uc, r'appendField\(head, sizeof\(head\), headLen, "(client_request_id)"'), FIELD_CRID),
        ("crid 필드(2차)", grab(ew, r'name=\\"(client_request_id)\\"'), FIELD_CRID),
        ("detect 경로", grab(uc, r'"(/api/v1/detect)"'), "/api/v1/detect"),
        ("enrich 경로", grab(uc, r'"(/api/v1/enrich)"'), "/api/v1/enrich"),
    ]
    rows += [(f"ToF 필드 {k}", grab(sc, rf'TOF_\w+_FIELD = "({k})"'), k) for k in TOF_FIELDS]
    ok = True
    for name, src, mine in rows:
        ok &= _check(f"[상수 대조] {name}", src == mine, f"원본={src} 수신기={mine}")
    return ok


def self_test():
    import hashlib
    import shutil
    import tempfile

    ok = True
    print("[상수 대조] 원본 파일 텍스트 vs 수신기 복제값")
    ok &= constant_checks()

    tmp = Path(tempfile.mkdtemp(prefix="record_receiver_selftest_"))
    try:
        out = tmp / "rec"
        app = create_app(out, "knock", "a")
        c = app.test_client()
        auth = {"Authorization": "Bearer TOKEN-MUST-NOT-LEAK"}

        def detect(crid, nbytes, tof=True):
            fields = [(FIELD_CRID, crid), ("device_id", "ddingdong-mic-uplink-001")]
            if tof:
                fields += [("tof_presence", "true"), ("tof_near_count", "12"), ("tof_motion_ndet", "3")]
            # peak 32767 한 개 + −32768 한 개 → clip 2, peak 32768
            pcm = (b"\xff\x7f" + b"\x00\x80" + b"\x10\x00" * (nbytes // 2))[:nbytes]
            body = board_multipart("ddingdongMicUplinkBoundary5C1E7", fields,
                                   [(FIELD_AUDIO, "audio.pcm", "application/octet-stream", pcm)])
            r = c.post("/api/v1/detect", data=body, headers=auth,
                       content_type="multipart/form-data; boundary=ddingdongMicUplinkBoundary5C1E7")
            return r, pcm

        def enrich(crid, nbytes):
            jpg = b"\xff\xd8\xff\xe0" + b"\x11" * 5000 + b"\xff\xd9"
            pcm = (b"\x00\x01" * (nbytes // 2 + 1))[:nbytes]
            body = board_multipart("ddingdongEnrichUplinkBoundary7A3F1", [(FIELD_CRID, crid)],
                                   [(FIELD_IMAGE, "shot.jpg", "image/jpeg", jpg),
                                    (FIELD_AUDIO, "audio.pcm", "application/octet-stream", pcm)])
            r = c.post("/api/v1/enrich", data=body, headers=auth,
                       content_type="multipart/form-data; boundary=ddingdongEnrichUplinkBoundary7A3F1")
            return r, pcm

        def n_files(sub):
            return len(list((out / sub).glob("*.wav")))

        print("\n[쌍 · 응답 대조]")
        r, pre_pcm = detect("e2-selftest-1", DETECT_AUDIO_BYTES)
        text = r.get_data(as_text=True)
        seen = r.get_data()[:RESP_MAX_BYTES].decode("utf-8", "replace")  # 보드가 보관하는 앞부분
        ok &= _check("detect 200 + pre 1개", (r.status_code, n_files("pre")) == (200, 1),
                     f"status={r.status_code} pre={n_files('pre')}")
        ok &= _check("응답 길이 ≤ 767 B", len(r.get_data()) <= RESP_MAX_BYTES, f"{len(r.get_data())} B")
        ok &= _check("보드 게이트 판독 = pending", board_peek(seen, "enrich_status") == "pending",
                     f"peek={board_peek(seen, 'enrich_status')!r} body={text}")
        ok &= _check("보드 cls 판독", board_peek(seen, "predicted_class") == "record_only",
                     f"peek={board_peek(seen, 'predicted_class')!r}")

        print("\n[NC-2 짝 맞추기]")
        r, _ = enrich("e2-unknown-9", ENRICH_AUDIO_BYTES)
        ok &= _check("NC-2 모르는 id → post 0개", (r.status_code, n_files("post")) == (404, 0),
                     f"status={r.status_code} post={n_files('post')}")

        r, post_pcm = enrich("e2-selftest-1", ENRICH_AUDIO_BYTES)
        ok &= _check("enrich 201 + post 1개", (r.status_code, n_files("post")) == (201, 1),
                     f"status={r.status_code} post={n_files('post')}")
        pre_f, post_f = out / "pre" / "direct_knock_a_01.wav", out / "post" / "direct_knock_a_01.wav"
        for name, f, pcm, frames in (("pre", pre_f, pre_pcm, DETECT_AUDIO_BYTES // 2),
                                     ("post", post_f, post_pcm, ENRICH_AUDIO_BYTES // 2)):
            if not f.exists():
                ok &= _check(f"{name} WAV 형식·무손실", False, f"{f.name} 없음")
                continue
            with wave.open(str(f), "rb") as w:
                got = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes())
                same = w.readframes(w.getnframes()) == pcm
            ok &= _check(f"{name} WAV 형식·무손실", got == (1, 2, SAMPLE_RATE, frames) and same,
                         f"(ch,width,rate,frames)={got} 바이트 일치={same}")
        r, _ = enrich("e2-selftest-1", ENRICH_AUDIO_BYTES)
        ok &= _check("같은 id 두 번째 enrich = orphan", (r.status_code, n_files("post")) == (404, 1),
                     f"status={r.status_code} post={n_files('post')}")

        print("\n[NC-1 크기 가드]")
        r, _ = detect("e2-selftest-short", DETECT_AUDIO_BYTES - 1)
        seen = r.get_data()[:RESP_MAX_BYTES].decode("utf-8", "replace")
        ok &= _check("NC-1 65,535 B → pre 파일 수 불변", n_files("pre") == 1, f"pre={n_files('pre')}")
        ok &= _check("NC-1 응답 = skipped", board_peek(seen, "enrich_status") == "skipped",
                     f"status={r.status_code} peek={board_peek(seen, 'enrich_status')!r}")
        detect("e2-selftest-2", DETECT_AUDIO_BYTES)
        r, _ = enrich("e2-selftest-2", ENRICH_AUDIO_BYTES - 2)
        ok &= _check("enrich 크기 불일치 → 400 · post 불변", (r.status_code, n_files("post")) == (400, 1),
                     f"status={r.status_code} post={n_files('post')}")
        r = c.post("/api/v1/detect", data={FIELD_CRID: "e2-nofile"}, headers=auth)
        ok &= _check("audio 누락 → 400 · pre 불변", (r.status_code, n_files("pre")) == (400, 2),
                     f"status={r.status_code} pre={n_files('pre')}")

        print("\n[NC-3 사진 미저장]")
        jpegs = [p for p in tmp.rglob("*") if p.is_file() and p.read_bytes()[:2] == b"\xff\xd8"]
        ok &= _check("NC-3 FF D8 시작 파일 0개", jpegs == [], f"{[p.name for p in jpegs]}")
        extra = sorted(p.relative_to(out).as_posix() for p in out.rglob("*")
                       if p.is_file() and p.suffix != ".wav" and p.name != "manifest.csv")
        ok &= _check("out-dir 에 wav·manifest 외 파일 0개", extra == [], f"{extra}")

        rows = list(csv.DictReader(open(out / "manifest.csv", encoding="utf-8")))
        first = rows[0] if rows else {}
        ok &= _check("manifest 첫 행 통계·ToF·auth",
                     (first.get("pre_peak"), first.get("pre_clip"), first.get("tof_near_count"),
                      first.get("tof_center_mm"), first.get("auth")) == ("32768", "2", "12", "", "있음"),
                     f"peak={first.get('pre_peak')} clip={first.get('pre_clip')} "
                     f"near={first.get('tof_near_count')} center={first.get('tof_center_mm')!r} auth={first.get('auth')}")
        raw = (out / "manifest.csv").read_text(encoding="utf-8")
        ok &= _check("manifest 에 토큰 값 없음", "TOKEN-MUST-NOT-LEAK" not in raw, "Bearer 값 미기록")
        ok &= _check("manifest status 순서",
                     [x["status"] for x in rows] == ["pre_saved", "orphan", "post_saved", "orphan", "rejected_size",
                                                     "pre_saved", "rejected_size", "rejected_missing_field"],
                     f"{[x['status'] for x in rows]}")

        print("\n[NC-4 재개 · 덮어쓰기 금지]")
        before = {p.name + p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*.wav")}
        app2 = create_app(out, "knock", "a")  # 재시작
        c = app2.test_client()
        ok &= _check("NC-4 재시작 다음 번호 = 3", app2.config["RECORD_STATE"]["next"] == 3,
                     f"next={app2.config['RECORD_STATE']['next']}")
        r, _ = detect("e2-selftest-3", DETECT_AUDIO_BYTES)
        ok &= _check("NC-4 재시작 후 take 03 저장", (out / "pre" / "direct_knock_a_03.wav").exists(),
                     f"status={r.status_code} pre={sorted(p.name for p in (out / 'pre').glob('*.wav'))}")
        after = {p.name + p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*.wav")}
        ok &= _check("NC-4 기존 파일 해시 불변", all(after.get(k) == v for k, v in before.items()),
                     f"기존 {len(before)}개 대조")
        squat = out / "pre" / "direct_knock_a_04.wav"
        squat.write_bytes(b"not-overwritten")
        r, _ = detect("e2-selftest-4", DETECT_AUDIO_BYTES)
        ok &= _check("같은 이름 존재 → 409 · 내용 불변",
                     (r.status_code, squat.read_bytes()) == (409, b"not-overwritten"), f"status={r.status_code}")
        ok &= _check("다른 유닛은 번호 독립(1부터)", create_app(out, "knock", "b").config["RECORD_STATE"]["next"] == 1, "unit b")

        print("\n[out-dir 가드]")
        inside = REPO_ROOT / "server" / "record_receiver_should_not_exist"
        try:
            validate_out_dir(str(inside))
            ok &= _check("repo 안 out-dir 거부", False, "통과해 버림")
        except SystemExit as exc:
            ok &= _check("repo 안 out-dir 거부", not inside.exists(), f"{exc.code}")
        ok &= _check("repo 밖 out-dir 허용", validate_out_dir(str(tmp / "x")) == (tmp / "x").resolve(), "tmp")
        try:
            create_app(out, "knock", "A")
            ok &= _check("대소문자만 다른 유닛 거부", False, "통과해 버림")
        except SystemExit as exc:
            ok &= _check("대소문자만 다른 유닛 거부", True, f"{exc.code}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        ok &= _check("임시 디렉터리 정리", not tmp.exists(), str(tmp))

    print("\n" + ("✅ self-test 전건 통과" if ok else "🔴 self-test 실패 — 수신기를 믿지 말 것"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="녹음 전용 수신기 (카톡·STT·DB 없음)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--self-test", action="store_true", help="임시 디렉터리에서 자기검증(포트 안 엶)")
    ap.add_argument("--out-dir", help="저장 폴더(repo 밖, 없으면 만든다) — 필수")
    ap.add_argument("--label", choices=LABELS, help="필수")
    ap.add_argument("--unit", help="유닛 id, 영문·숫자만(밑줄 금지) — 필수")
    ap.add_argument("--port", type=int, help="보드 secrets.h SPIKE_SERVER_PORT 와 같게 — 필수")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    missing = [f"--{k.replace('_', '-')}" for k in ("out_dir", "label", "unit", "port") if getattr(args, k) is None]
    if missing:
        ap.error(f"필수 인자 누락: {' '.join(missing)} (기본값 없음)")
    if not UNIT_RE.match(args.unit):
        ap.error(f"--unit '{args.unit}' 은 영문·숫자만 허용한다(밑줄 금지 — D3 source_key 가 끝의 _숫자를 테이크로 뗀다)")
    if not 1 <= args.port <= 65535:
        ap.error(f"--port {args.port} 범위 밖(1~65535)")

    out = validate_out_dir(args.out_dir)
    app = create_app(out, args.label, args.unit)
    print("=" * 64)
    print("녹음 전용 수신기 — 카톡·STT·DB 없음")
    print(f"  label · unit   : {args.label} · {args.unit}")
    print(f"  다음 테이크    : {app.config['RECORD_STATE']['next']:02d}")
    print(f"  출력 경로      : {out}")
    print(f"  수신           : http://0.0.0.0:{args.port}/api/v1/detect · /api/v1/enrich")
    print("=" * 64, flush=True)
    app.run(host="0.0.0.0", port=args.port, threaded=False)  # 보드 1대 직렬 요청 — 단일 스레드라 상태 락 불요
    return 0


if __name__ == "__main__":
    sys.exit(main())
