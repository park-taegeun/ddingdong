#!/usr/bin/env python3
"""시연 기동 도구 — 터널 · 서버(실모델) · 대시보드를 명령 하나로 띄우고 단계마다 확인한다.

**성격 = 배관(plumbing)**. 부스 · 리허설 · 보드 세션마다 손으로 하던 기동 순서(터널 → 새 주소 반영 →
실모델 서버 → 관통 401 → 카카오 속도 → 대시보드)와 그 확인을 고정한다. 판정 · 임계값 · 제품 상태
어휘를 새로 만들지 않는다 — 서버 응답 어휘(expired · degraded · none …)를 **그대로** 읽는다.
- 배경 사고: 새 터널 주소 반영 누락(카톡 사진 회색 박스 · 대시보드 「사진을 불러올 수 없어요」) ·
  떠 있던 mock 서버에 실측 기록 · 하루 넘게 남은 서버가 다음 작업을 막음 · 터널 창에 명령을 붙여
  터널이 죽음.
- `server/app` 을 import 하지 않는다 — import 하는 순간 app/config.py 가 load_dotenv(server/.env)
  를 실행한다. 필요한 상수(env 이름 · 경로 · 상태 값)는 아래에 **복제**하고 `--self-test` 가 원본
  파일을 **텍스트로** 읽어 대조한다.

🔴 server/.env 를 쓰지 않는다
- 터널 주소는 **서버 자식 프로세스 환경 변수** DDINGDONG_CAPTURE_URL_BASE=<터널>/captures 로만 넣는다.
  근거 = app/config.py 의 load_dotenv 는 override 기본값 False 라 이미 있는 환경 변수를 덮지 않는다
  (venv_real 에 설치된 python-dotenv 소스 — `--self-test` 가 텍스트로 대조).
- 대가: 이 도구 없이 손으로 서버를 띄우면 .env 의 옛 주소가 쓰인다(요약에 1줄로 알린다).

모드 (`--mode` 필수 — 기본값 없음)
- live = 부스 · 리허설. 카톡 · 자막 실제(server/.env 의 자격 그대로 — 셸에 같은 이름의 변수가 있어도
  자식 환경에서 지워 .env 가 이기게 한다). cloudflared quick tunnel 을 띄우고 그 주소를 주입한다.
- dry  = 보드 실측(카톡 0 · CSR 0). 터널 없음. 카카오 4키 · NCP 2키를 자식 환경에서 **빈 문자열**로
  덮는다(빈 값도 "이미 있는 환경 변수"라 .env 가 못 덮는다). DB · 캡처 폴더는 실행 폴더 안에 새로 만든다
  → 토큰 행이 없고 KAKAO_REFRESH_TOKEN 이 비어 부트스트랩이 네트워크 전에 실패(미발송 기록, 5xx 없음),
  NCP 키가 비어 STT 는 mock(호출 0).

동작 순서 (실패하면 그때까지 띄운 자식을 전부 정리하고 종료)
  0 인자 검증          --mode · --model-path(있는 폴더) · --log-dir(repo 밖) · --port 전부 필수
  1 사전 점검          포트 LISTEN(있으면 lsof 결과만 보이고 kill 없이 종료) · 실행 파일 · .env 키 이름
  2 카카오 속도(live)  kapi.kakao.com 왕복 초. 1초 넘으면 ⚠️(멈추지 않음)
  3 터널(live)         cloudflared quick tunnel → 출력에서 주소 추출
  4 서버               venv_real/bin/flask run → /api/v1/notifications 무인증 401 = 준비
  5 실모델 확인        서버 PID 의 RSS · tensorflow 라이브러리 매핑 수(mock 방지)
  6 serving_level      기동 로그의 serving_level: 줄을 그대로 표시(peak rule=peak_plain_v1 기대)
  7 터널 관통(live)    https://<터널>/api/v1/notifications → 401
  8 상태(읽기 전용)    /api/v1/stats system_health · /api/v1/registration (DASHBOARD_TOKEN 은 메모리로만)
  9 대시보드(선택)     --dashboard 면 dashboard/ 에서 npm run dev → Local: 주소
 10 요약               ✅/⚠️/❌ 표 · PID · 로그 경로 → 실행 폴더 summary.txt (터널 주소는 화면에만)
 11 실시간 표시        서버: POST /api/v1/… · WARNING · ERROR · Traceback 줄만(같은 WARNING 은 1회).
                      터널: ERR 줄만. 전체는 실행 폴더의 로그 파일에.
 12 Ctrl+C            자식 역순 정리(프로세스 그룹 · SIGTERM → 시간 초과면 SIGKILL) → 포트 LISTEN 0 → CLEAN

종료 코드
  0  정상 종료(Ctrl+C 뒤 CLEAN)
  2  인자 · 사전 점검 실패(자식을 띄우기 전)
  3  기동 확인 실패(터널 주소 · 401 · 실모델 · 상태 기대값 · 대시보드 주소)
  4  서버 자식 비정상 종료
  5  정리 뒤에도 포트 LISTEN 이 남음(CLEAN 아님)
  1  --self-test 실패

⚠️ 실행 폴더(<log-dir>/run-YYYYmmdd-HHMMSS/) = 공유 금지 — 터널 로그에 터널 주소, dry 캡처에 방문자
사진이 남는다. 그래서 --log-dir 는 repo 밖만 허용한다.
⚠️ 대시보드 dev 프록시는 localhost:5000 고정(dashboard/vite.config.ts) — --port 가 5000 이 아니면 대시보드가
서버에 못 붙는다(요약에 ⚠️).

--------------------------------------------------------------------------------
학부생 사용법
--------------------------------------------------------------------------------
1) 자기검증(수 초, 포트 · 네트워크 · 자식 프로세스 0):
     cd "<repo>/server"
     venv/bin/python3 tools/demo_up.py --self-test
2) 부스 · 리허설(live):
     venv/bin/python3 tools/demo_up.py --mode live \\
         --model-path "$HOME/ddingdong_runs/<J run 폴더>/inference_savedmodel" \\
         --log-dir "$HOME/ddingdong-측정결과/$(date +%F)/demo_up" --port 5000 --dashboard
3) 보드 실측(dry, 카톡 · CSR 0): 2) 에서 --mode dry 로만 바꾼다.
4) 끝낼 때 = 이 창에서 Ctrl+C 한 번 → `CLEAN` 확인. 이 창에 다른 명령을 붙이지 않는다.
"""

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "server"
DASHBOARD_DIR = REPO_ROOT / "dashboard"
ENV_FILE = SERVER_DIR / ".env"
FLASK_BIN = SERVER_DIR / "venv_real" / "bin" / "flask"

# ── 계약 상수 (복제) ────────────────────────────────────────────────────────────
# ⚠️ 동기화 필요: 아래 값은 원본 파일의 복제다. `--self-test` 의 [원본 대조] 가 불일치를 FAIL 로 드러낸다.
KAKAO_KEYS = ("KAKAO_REST_API_KEY", "KAKAO_CLIENT_SECRET", "KAKAO_ACCESS_TOKEN", "KAKAO_REFRESH_TOKEN")  # config.py
NCP_KEYS = ("NCP_CLIENT_ID", "NCP_CLIENT_SECRET")                   # config.py · stt.is_real_mode
SILENCED_KEYS = KAKAO_KEYS + NCP_KEYS                                # dry 에서 빈 값 / live 에서 상속 제거
ENV_DB = "DATABASE_URL"                                              # config.py
ENV_CAPTURE_DIR = "DDINGDONG_CAPTURE_DIR"                            # config.py
ENV_CAPTURE_URL_BASE = "DDINGDONG_CAPTURE_URL_BASE"                  # config.py → image_store.public_url
ENV_MODEL_PATH = "DDINGDONG_MODEL_PATH"                              # config.py
TOKEN_KEYS = ("DEVICE_TOKEN", "DASHBOARD_TOKEN")                     # config.py · auth.py
CAPTURE_ROUTE = "/captures"                                          # captures.py 라우트 · config.py 기본값
SERVING_LEVEL_MARK = "serving_level: /detect 추론 입력 = "          # app/__init__.py 기동 WARNING
SERVING_LEVEL_EXPECTED = "peak rule=peak_plain_v1"                   # J = 4클래스 peak · 규칙 plain
HEALTH_KEYS = ("device_status", "kakao_token_status", "kakao_token_expires_in_minutes", "clova_api_status")  # routes.py
KAKAO_ROW_ABSENT = ("expired", 0)    # routes._kakao_token_health: 행 부재 → ("expired", 0)
CLOVA_MOCK = "degraded"              # routes system_health: stt.is_real_mode() False
VITE_PROXY_TARGET = "http://localhost:5000"                          # dashboard/vite.config.ts
DASHBOARD_PORT = 5173                                                # vite 기본

# 실모델 판정: 실측 3축 기록(RSS 461,280 ~ 475,920 KB · TF 매핑 54)의 자릿수만 쓴다. 그날 값이 흔들리므로
# 정확 일치는 요구하지 않는다. mock(TF 미로드) 서버는 TF 매핑 0 · RSS 수만 KB 자릿수라 둘 다 미달.
REAL_MODEL_MIN_RSS_KB = 300_000
REAL_MODEL_MIN_TF_MAPS = 1

KAKAO_API = "https://kapi.kakao.com"
KAKAO_SLOW_SEC = 1.0
NOTIFICATIONS_PATH = "/api/v1/notifications"
UA = {"User-Agent": "ddingdong-demo-up"}
TUNNEL_URL_WAIT_SEC = 45
SERVER_READY_WAIT_SEC = 180     # TF 로드 + warmup
TUNNEL_401_WAIT_SEC = 90        # quick tunnel DNS 전파
DASHBOARD_WAIT_SEC = 60
STOP_GRACE_SEC = 8

# quick tunnel 주소 = 하이픈으로 이은 단어들.trycloudflare.com. 같은 줄 계열에 나오는 API 주소
# (https://api.trycloudflare.com — cloudflared 바이너리 문자열)는 하이픈이 없어 걸리지 않는다.
TUNNEL_RE = re.compile(r"https://([a-z0-9]+(?:-[a-z0-9]+)+)\.trycloudflare\.com\b")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
UNSUPPORTED = object()   # .env 줄이 이 파서의 지원 범위 밖 — 값을 추측하지 않고 실패로 드러낸다


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ── 순수 판단 (자기검증 대상) ─────────────────────────────────────────────────────
def strip_ansi(s):
    return ANSI_RE.sub("", s)


def extract_tunnel_url(line):
    """cloudflared 출력 한 줄 → quick tunnel 주소 또는 None."""
    m = TUNNEL_RE.search(strip_ansi(line))
    return m.group(0) if m else None


def parse_env_text(text):
    """server/.env 텍스트 → {키: 값}. python-dotenv 1.2.x 와 같은 결과가 나는 범위만 다룬다.

    같은 키는 마지막 줄이 이긴다(dotenv 도 순서대로 dict 에 넣는다). `=` 없는 줄 = None(설정 안 됨).
    범위 밖(${} 보간 · 역슬래시 이스케이프 · 닫히지 않은 따옴표 · 따옴표 키) = UNSUPPORTED.
    """
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?:export\s+)?([^=#\s]+)\s*(=?)\s*(.*)$", line)
        if not m:
            continue
        key, eq, rest = m.groups()
        if key.startswith("'"):
            out[key.strip("'")] = UNSUPPORTED
            continue
        if not eq:
            out[key] = None
            continue
        if "${" in rest or "\\" in rest:
            out[key] = UNSUPPORTED
            continue
        if rest[:1] in ("'", '"'):
            end = rest.find(rest[0], 1)
            tail = rest[end + 1:].strip() if end > 0 else ""
            out[key] = rest[1:end] if end > 0 and (not tail or tail.startswith("#")) else UNSUPPORTED
        else:
            out[key] = re.sub(r"\s+#.*", "", rest).rstrip()
    return out


def effective_value(key, env_text, environ):
    """서버가 보게 될 값. 이미 있는 환경 변수가 이긴다(load_dotenv override=False) → 아니면 .env 마지막 줄."""
    if key in environ:
        return environ[key]
    v = parse_env_text(env_text).get(key)
    if v is UNSUPPORTED:
        raise Fail(2, f"server/.env 의 {key} 줄이 이 도구의 파서 범위 밖(보간 · 이스케이프 · 따옴표) — 값은 출력하지 않는다")
    return v


def token_key_rows(env_text, environ):
    """토큰 키 존재 점검 → [(표시, 항목, 상세)]. 값은 절대 담지 않는다(있음/빈 값 · 출처만)."""
    rows = []
    for k in TOKEN_KEYS:
        src = "셸 환경 변수" if k in environ else "server/.env"
        v = effective_value(k, env_text, environ)
        rows.append(("✅", f"{k}", f"있음({src})") if v else ("❌", f"{k}", f"없음 또는 빈 값({src}) — 인증이 항상 실패한다"))
    return rows


def child_env_overrides(mode, tunnel_url, run_dir, model_path):
    """모드별 서버 자식 환경 덮어쓰기. 값 None = 상속 환경에서 지운다."""
    o = {"FLASK_APP": "app", ENV_MODEL_PATH: str(model_path), "PYTHONDONTWRITEBYTECODE": "1"}
    if mode == "dry":
        o.update({k: "" for k in SILENCED_KEYS})
        o[ENV_DB] = "sqlite:///" + str(Path(run_dir) / "ddingdong.db")
        o[ENV_CAPTURE_DIR] = str(Path(run_dir) / "captures")
        o[ENV_CAPTURE_URL_BASE] = CAPTURE_ROUTE   # .env 의 옛 터널 주소 대신 로컬 서빙 라우트
    elif mode == "live":
        if not tunnel_url:
            raise ValueError("live 모드에는 터널 주소가 필요하다")
        o.update({k: None for k in SILENCED_KEYS})   # 셸의 빈 값이 .env 자격을 이기지 못하게
        o[ENV_CAPTURE_URL_BASE] = tunnel_url.rstrip("/") + CAPTURE_ROUTE
    else:
        raise ValueError(mode)
    return o


def apply_overrides(base, overrides):
    env = dict(base)
    for k, v in overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return env


def listen_busy(lsof_stdout):
    """`lsof -nP -iTCP:<port> -sTCP:LISTEN` 출력 → LISTEN 있음? (없으면 lsof 는 아무것도 안 찍는다)"""
    return bool(lsof_stdout.strip())


def real_model_ok(rss_kb, tf_maps):
    return rss_kb >= REAL_MODEL_MIN_RSS_KB and tf_maps >= REAL_MODEL_MIN_TF_MAPS


def validate_log_dir(raw):
    """repo 안이면 거부(심볼릭 링크를 풀고 비교). 통과하면 절대 경로."""
    p = Path(raw).expanduser().resolve()
    if p == REPO_ROOT or REPO_ROOT in p.parents:
        raise Fail(2, f"--log-dir 가 repo 안이다({p}) — 사진 · 터널 주소 커밋 방지를 위해 거부. repo 밖 경로를 준다.")
    return p


def server_line_shown(line):
    """서버 로그 한 줄을 화면에 보일까. 대시보드 폴링 GET 은 숨긴다(전체는 파일에)."""
    s = strip_ansi(line)
    return '"POST /api/v1/' in s or "Traceback" in s or re.search(r"\b(WARNING|ERROR|CRITICAL)\b", s) is not None


def judge_health(mode, health, reg):
    """/stats system_health · /registration → ([(표시, 항목, 상세)], dry 전제 성립?)."""
    rows, ok = [], True
    dev = health["device_status"]
    rows.append(("✅" if dev == "online" else "⚠️", "기기", f"{dev}(보드 heartbeat 전이면 offline 이 정상)"))
    kakao = (health["kakao_token_status"], health["kakao_token_expires_in_minutes"])
    clova = health["clova_api_status"]
    if mode == "dry":
        k_ok, c_ok = kakao == KAKAO_ROW_ABSENT, clova == CLOVA_MOCK
        ok = k_ok and c_ok
        rows.append(("✅" if k_ok else "❌", "카카오 토큰", f"{kakao[0]} · 남은 {kakao[1]}분 (dry 기대 = expired · 0 = 행 없음)"))
        rows.append(("✅" if c_ok else "❌", "Clova", f"{clova} (dry 기대 = {CLOVA_MOCK})"))
    else:
        rows.append(("✅" if kakao[0] == "valid" else "⚠️", "카카오 토큰", f"{kakao[0]} · 남은 {kakao[1]}분"))
        rows.append(("✅" if clova == "ok" else "⚠️", "Clova", clova))
    rows.append(("✅", "초인종 등록", f"{reg['state']} (수집 {reg['collected']})"))
    return rows, ok


def format_rows(rows):
    return "\n".join(f"  {mark} {item:<16} {detail}" for mark, item, detail in rows)


# ── 프로세스 · 네트워크 ──────────────────────────────────────────────────────────
def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def lsof_listen(port):
    return run_cmd(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"])


def measure_proc(pid):
    rss = run_cmd(["ps", "-o", "rss=", "-p", str(pid)]).strip()
    paths = {ln[1:] for ln in run_cmd(["lsof", "-p", str(pid), "-Fn"]).splitlines()
             if ln.startswith("n") and "tensorflow" in ln}
    return int(rss or 0), len(paths)


def http_status(url, token=None, timeout=5):
    """상태 코드(HTTP 오류 포함) · 응답 본문. 연결 실패 = (None, 예외 이름)."""
    headers = dict(UA)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:  # URLError · timeout · 연결 거부
        return None, type(exc).__name__


def kakao_rtt():
    t = time.monotonic()
    code, err = http_status(KAKAO_API, timeout=5)
    return (None, err) if code is None else (time.monotonic() - t, None)


class Child:
    def __init__(self, name, cmd, cwd, env, log_path):
        self.name, self.log_path, self.pos, self.buf, self.reported = name, log_path, 0, "", False
        with open(log_path, "ab") as f:
            # 새 세션 = 자기 프로세스 그룹. 터미널 Ctrl+C 가 자식에 직접 가지 않고, 정리는 그룹 단위로 한다.
            self.proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=f, stderr=subprocess.STDOUT,
                                         stdin=subprocess.DEVNULL, start_new_session=True)

    def new_lines(self):
        with open(self.log_path, "rb") as f:
            f.seek(self.pos)
            data = f.read()
        self.pos += len(data)
        *lines, self.buf = (self.buf + data.decode("utf-8", "replace")).split("\n")
        return lines

    def stop(self):
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + STOP_GRACE_SEC
        while time.monotonic() < deadline:
            self.proc.poll()   # 그룹 리더 좀비를 거둬야 그룹이 비었는지 보인다
            try:
                os.killpg(self.proc.pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.2)
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.proc.pid, signal.SIGKILL)
        self.proc.wait()


def wait_line(child, pick, timeout, what):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for ln in child.new_lines():
            v = pick(ln)
            if v:
                return v
        if child.proc.poll() is not None:
            raise Fail(4 if child.name == "server" else 3, f"{child.name} 자식이 {what} 전에 종료(코드 {child.proc.returncode}) — {child.log_path}")
        time.sleep(0.3)
    raise Fail(3, f"{timeout}초 안에 {what} 실패 — {child.log_path}")


# ── 본 흐름 ─────────────────────────────────────────────────────────────────────
def main_run(args):
    model_path = Path(args.model_path).expanduser().resolve()
    if not model_path.is_dir():
        raise Fail(2, f"--model-path 폴더가 없다: {model_path}")
    if not 1 <= args.port <= 65535:
        raise Fail(2, f"--port {args.port} 범위 밖(1~65535)")
    run_dir = validate_log_dir(args.log_dir) / f"run-{datetime.now():%Y%m%d-%H%M%S}"
    run_dir.mkdir(parents=True)
    st = {"rows": [], "children": [], "run_dir": run_dir, "notes": []}
    print(f"실행 폴더(공유 금지): {run_dir}", flush=True)
    try:
        code = boot_and_watch(args, model_path, st)
    except Fail as exc:
        st["rows"].append(("❌", "실패", str(exc)))
        print(f"\n❌ {exc}", flush=True)
        code = exc.code
    except KeyboardInterrupt:
        print("\n중단 신호(Ctrl+C · SIGTERM · SIGHUP) — 정리 시작", flush=True)
        code = 0
    except Exception as exc:   # 예상 밖 오류도 자식을 남기지 않는다
        st["rows"].append(("❌", "예상 밖 오류", type(exc).__name__))
        print(f"\n❌ 예상 밖 오류 {type(exc).__name__}: {exc}", flush=True)
        code = 3
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):   # 정리 중 두 번째 신호로 자식이 남지 않게
            signal.signal(sig, signal.SIG_IGN)
        for c in reversed(st["children"]):
            c.stop()
        ports = [args.port] + ([DASHBOARD_PORT] if args.dashboard else [])
        # 자식을 하나도 안 띄웠으면 잔존 검사 대상이 없다 — 사전 점검이 본 남의 LISTEN 을 자기 잔존으로 세지 않는다
        left = {p: lsof_listen(p) for p in ports} if st["children"] else {}
        busy = {p: out for p, out in left.items() if listen_busy(out)}
        alive = [c.name for c in st["children"] if c.proc.poll() is None]
        (run_dir / "summary.txt").write_text(
            format_rows(st["rows"]) + "\n" + "\n".join(st["notes"]) + "\n"
            + f"정리: LISTEN 잔존 {sorted(busy) or '없음'} · 살아 있는 자식 {alive or '없음'}\n", encoding="utf-8")
    if busy or alive:
        for p, out in busy.items():
            print(f"⚠️ 포트 {p} LISTEN 잔존:\n{out}")
        print(f"⚠️ 정리 미완 — 살아 있는 자식 {alive}", flush=True)
        return 5
    print("CLEAN", flush=True)
    return code


def boot_and_watch(args, model_path, st):
    rows, run_dir, live = st["rows"], st["run_dir"], args.mode == "live"

    # 1 사전 점검 — 아무것도 띄우기 전
    ports = [args.port] + ([DASHBOARD_PORT] if args.dashboard else [])
    for p in ports:
        out = lsof_listen(p)
        if listen_busy(out):
            raise Fail(2, f"포트 {p} 에 이미 LISTEN 이 있다(kill 하지 않는다 — 주인을 확인해 직접 종료):\n{out}")
    need = [("lsof", shutil.which("lsof"))]
    need += [("cloudflared", shutil.which("cloudflared"))] if live else []
    need += [("npm", shutil.which("npm"))] if args.dashboard else []
    need += [("server/venv_real/bin/flask", str(FLASK_BIN) if os.access(FLASK_BIN, os.X_OK) else None)]
    missing = [n for n, p in need if not p]
    if missing:
        raise Fail(2, f"실행 파일 없음: {', '.join(missing)}")
    if not ENV_FILE.is_file():
        raise Fail(2, "server/.env 가 없다")
    env_text = ENV_FILE.read_text(encoding="utf-8")
    key_rows = token_key_rows(env_text, os.environ)
    rows += key_rows
    if any(r[0] == "❌" for r in key_rows):
        raise Fail(2, "토큰 키 점검 실패(위 표)")
    dash_token = effective_value("DASHBOARD_TOKEN", env_text, os.environ)
    if args.dashboard and args.port != 5000:
        rows.append(("⚠️", "대시보드 프록시", f"vite 프록시는 {VITE_PROXY_TARGET} 고정 — --port {args.port} 에는 못 붙는다"))
    rows.append(("✅", "사전 점검", f"포트 {ports} 빔 · 실행 파일 · .env 키 이름"))

    # 2 카카오 속도
    if live:
        sec, err = kakao_rtt()
        if sec is None:
            rows.append(("⚠️", "카카오 속도", f"연결 실패({err}) — 핫스팟 off/on 뒤 다시"))
        else:
            rows.append(("✅" if sec <= KAKAO_SLOW_SEC else "⚠️", "카카오 속도",
                         f"{sec:.2f}초" + ("" if sec <= KAKAO_SLOW_SEC else " — 1초 초과: 핫스팟 off/on 뒤 다시")))

    # 3 터널
    tunnel_url = None
    if live:
        t = Child("tunnel", ["cloudflared", "tunnel", "--url", f"http://localhost:{args.port}"],
                  SERVER_DIR, dict(os.environ), run_dir / "tunnel.log")
        st["children"].append(t)
        tunnel_url = wait_line(t, extract_tunnel_url, TUNNEL_URL_WAIT_SEC, "터널 주소 추출")
        rows.append(("✅", "터널", "주소 확보(화면에만 표시)"))
        print(f"터널 주소: {tunnel_url}", flush=True)

    # 4 서버
    env = apply_overrides(os.environ, child_env_overrides(args.mode, tunnel_url, run_dir, model_path))
    s = Child("server", [str(FLASK_BIN), "run", "--host=0.0.0.0", f"--port={args.port}"],
              SERVER_DIR, env, run_dir / "server.log")
    st["children"].append(s)
    local = f"http://127.0.0.1:{args.port}"
    deadline = time.monotonic() + SERVER_READY_WAIT_SEC
    while http_status(local + NOTIFICATIONS_PATH)[0] != 401:
        if s.proc.poll() is not None:
            raise Fail(4, f"서버 자식이 준비 전에 종료(코드 {s.proc.returncode}) — {s.log_path}")
        if time.monotonic() > deadline:
            raise Fail(3, f"{SERVER_READY_WAIT_SEC}초 안에 무인증 401 미확인 — {s.log_path}")
        time.sleep(1)
    rows.append(("✅", "서버 준비", f"무인증 {NOTIFICATIONS_PATH} → 401"))

    # 5 실모델
    rss, tf = measure_proc(s.proc.pid)
    verdict = real_model_ok(rss, tf)
    rows.append(("✅" if verdict else "❌", "실모델", f"RSS {rss:,} KB · TF 매핑 {tf} (기준 RSS ≥ {REAL_MODEL_MIN_RSS_KB:,} 그리고 TF ≥ {REAL_MODEL_MIN_TF_MAPS})"))
    if not verdict:
        raise Fail(3, "실모델 판정 미달 — mock 서버 의심")

    # 6 serving_level
    log_text = strip_ansi(s.log_path.read_text(encoding="utf-8", errors="replace"))
    sl = [ln for ln in log_text.splitlines() if SERVING_LEVEL_MARK in ln]
    sl_val = sl[-1].split(SERVING_LEVEL_MARK, 1)[1] if sl else "(줄 없음)"
    rows.append(("✅" if sl_val.startswith(SERVING_LEVEL_EXPECTED + " ") else "⚠️", "serving_level", sl_val))

    # 7 터널 관통
    if live:
        deadline, last = time.monotonic() + TUNNEL_401_WAIT_SEC, None
        while True:
            last = http_status(tunnel_url + NOTIFICATIONS_PATH, timeout=10)[0]
            if last == 401:
                break
            if t.proc.poll() is not None:
                raise Fail(3, f"터널 자식이 관통 확인 전에 종료 — {t.log_path}")
            if time.monotonic() > deadline:
                raise Fail(3, f"{TUNNEL_401_WAIT_SEC}초 안에 터널 경유 401 미확인(마지막 {last})")
            time.sleep(3)
        rows.append(("✅", "터널 관통", f"터널 경유 {NOTIFICATIONS_PATH} → 401"))

    # 8 상태(읽기 전용)
    code, body = http_status(local + "/api/v1/stats", token=dash_token)
    rcode, rbody = http_status(local + "/api/v1/registration", token=dash_token)
    if code != 200 or rcode != 200:
        raise Fail(3, f"상태 조회 실패 /stats {code} · /registration {rcode} (401 = DASHBOARD_TOKEN 불일치)")
    h_rows, h_ok = judge_health(args.mode, json.loads(body)["system_health"], json.loads(rbody))
    rows += h_rows
    if not h_ok:
        raise Fail(3, "dry 기대 상태가 아니다 — 카톡 0 · CSR 0 전제가 깨졌다")

    # 9 대시보드
    if args.dashboard:
        d = Child("dashboard", ["npm", "run", "dev", "--", "--strictPort"], DASHBOARD_DIR,
                  dict(os.environ), run_dir / "dashboard.log")
        st["children"].append(d)
        url = wait_line(d, lambda ln: (re.search(r"Local:\s+(\S+)", strip_ansi(ln)) or [None, None])[1],
                        DASHBOARD_WAIT_SEC, "대시보드 Local: 주소")
        rows.append(("✅", "대시보드", url))

    # 10 요약
    if live:
        st["notes"].append("ℹ️ 새 터널 주소는 이 서버 자식 환경에만 있다 — 이 도구 없이 손으로 띄우면 server/.env 의 옛 주소가 쓰인다.")
        st["notes"].append("ℹ️ 카카오 토큰이 만료 상태면 첫 실제 알림이 갱신한다(망 정상일 때) — 리허설이면 테스트 발송 1회 권장(자동 발송 안 함).")
    pids = " · ".join(f"{c.name} {c.proc.pid}" for c in st["children"])
    logs = " · ".join(c.log_path.name for c in st["children"])
    st["notes"].append(f"자식 PID: {pids}")
    st["notes"].append(f"로그: {run_dir}/{{{logs}}}")
    print("\n" + "=" * 72)
    print(f"demo_up — mode {args.mode} · port {args.port}")
    print(format_rows(rows))
    print("\n".join(st["notes"]))
    if live:
        print(f"터널 주소(화면 전용): {tunnel_url}")
    print("=" * 72)
    print("실시간: POST /api/v1/… · WARNING · ERROR 만 표시. 끝내려면 Ctrl+C 한 번.", flush=True)

    # 11 실시간 표시
    seen = set()
    while True:
        for c in st["children"]:
            for ln in c.new_lines():
                s_ln = strip_ansi(ln)
                if c.name == "server" and server_line_shown(ln):
                    key = re.sub(r"^\[[^\]]*\]\s*", "", s_ln)
                    if "WARNING" in key and key in seen:
                        continue
                    seen.add(key)
                    print(f"[server] {s_ln}", flush=True)
                elif c.name == "tunnel" and " ERR " in s_ln:
                    print(f"[tunnel] {s_ln}", flush=True)
            if c.proc.poll() is not None and not c.reported:
                c.reported = True
                if c.name == "server":
                    rows.append(("❌", "서버", f"비정상 종료(코드 {c.proc.returncode})"))
                    raise Fail(4, f"서버 자식이 종료됐다(코드 {c.proc.returncode}) — {c.log_path}")
                msg = ("터널이 죽었다 — 문자 알림은 살아 있고 카톡 사진 · 대시보드 사진만 죽는다. 다시 띄우려면 Ctrl+C 뒤 재기동"
                       if c.name == "tunnel" else "대시보드가 죽었다 — 서버 · 알림은 영향 없음")
                rows.append(("⚠️", c.name, msg))
                print("\n" + "⚠️ " * 12 + f"\n⚠️ {msg}\n" + "⚠️ " * 12, flush=True)
        time.sleep(0.5)


# ── 자기검증 (record_receiver.py --self-test 선례: 파일 내 함수 + _check PASS/FAIL 줄) ──
def _check(name, passed, detail):
    print(f"  [{'PASS' if passed else 'FAIL'}] {name:<34} {detail}")
    return passed


def constant_checks():
    ok = True

    def has(rel, needle):
        p = REPO_ROOT / rel
        return p.is_file() and needle in p.read_text(encoding="utf-8")

    config_text = (SERVER_DIR / "app" / "config.py").read_text(encoding="utf-8")

    print("\n[원본 대조 — 텍스트]")
    for k in SILENCED_KEYS + (ENV_DB, ENV_CAPTURE_DIR, ENV_CAPTURE_URL_BASE, ENV_MODEL_PATH) + TOKEN_KEYS:
        ok &= _check(f"config.py 가 {k} 를 읽음", re.search(r'os\.environ\.get\(\s*"' + k + '"', config_text) is not None, "")
    ok &= _check("config.py 캡처 URL 기본값", has("server/app/config.py", f'"{ENV_CAPTURE_URL_BASE}", "{CAPTURE_ROUTE}"'), CAPTURE_ROUTE)
    ok &= _check("captures.py 라우트", has("server/app/captures.py", f'"{CAPTURE_ROUTE}/<opaque_id>"'), "")
    ok &= _check("image_store base 결합", has("server/app/image_store.py", '.rstrip("/")')
                 and has("server/app/image_store.py", 'f"{base}/{opaque_id}"'), "rstrip + /id")
    ok &= _check("__init__ serving_level 문구", has("server/app/__init__.py", f'"{SERVING_LEVEL_MARK}%s rule=%s'), "")
    for k in HEALTH_KEYS:
        ok &= _check(f"routes system_health {k}", has("server/app/routes.py", f'"{k}":'), "")
    ok &= _check("routes 행 부재 = expired · 0", has("server/app/routes.py", 'return "expired", 0'), "")
    ok &= _check("routes Clova mock = degraded", has("server/app/routes.py", f'else "{CLOVA_MOCK}"'), "")
    ok &= _check("constants 등록 none", has("server/app/constants.py", 'REGISTRATION_STATE_NONE = "none"'), "")
    ok &= _check("kakao 부트스트랩 refresh 빈 값 → 예외", has("server/app/kakao.py",
                 'if not refresh_token:\n        raise KakaoTokenError('), "네트워크 전")
    ok &= _check("stt NCP 둘 다 있어야 real", has("server/app/stt.py",
                 'return bool(current_app.config.get("NCP_CLIENT_ID")) and bool('), "")
    ok &= _check("auth Bearer 접두", has("server/app/auth.py", 'prefix = "Bearer "'), "")
    ok &= _check("vite 프록시 대상", has("dashboard/vite.config.ts", f'target: "{VITE_PROXY_TARGET}"'), "")
    dm = sorted((SERVER_DIR / "venv_real" / "lib").glob("python*/site-packages/dotenv/main.py"))
    dtext = dm[0].read_text(encoding="utf-8") if dm else ""
    ok &= _check("venv_real dotenv override 기본 False", "override: bool = False" in dtext
                 and "if k in os.environ and not self.override:" in dtext, dm[0].parents[2].name if dm else "없음")
    return ok


def self_test():
    ok = constant_checks()
    secret = "SELFTEST-SECRET-7f3a91c2"
    out_buf, err_buf = io.StringIO(), io.StringIO()
    tmp = Path(tempfile.mkdtemp(prefix="demo_up_selftest_"))
    try:
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            ok &= _body_checks(tmp, secret)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    printed = out_buf.getvalue() + err_buf.getvalue()
    sys.stdout.write(printed)
    print("\n[시크릿 미출력]")
    ok &= _check("자기검증 전 경로 stdout · stderr", printed.count(secret) == 0, f"고유 문자열 {printed.count(secret)}회")
    ok &= _check("임시 디렉터리 정리", not tmp.exists(), "")
    print("\n" + ("✅ self-test 전건 통과" if ok else "🔴 self-test 실패 — 이 도구를 믿지 말 것"))
    return 0 if ok else 1


def _body_checks(tmp, secret):
    ok = True
    print("\n[터널 주소 추출]")
    good = "https://alpha-bravo-charlie-delta.trycloudflare.com"
    ok &= _check("주소 줄", extract_tunnel_url(f"2026-01-01T00:00:00Z INF |  {good}   |") == good, "")
    ok &= _check("API 주소 줄 거부", extract_tunnel_url(
        'ERR failed to request quick Tunnel: Post "https://api.trycloudflare.com/tunnel"') is None, "api.trycloudflare.com")
    ok &= _check("안내 문구 줄 = 없음", extract_tunnel_url("INF Requesting new quick Tunnel on trycloudflare.com...") is None, "")
    ok &= _check("ANSI 색 감싼 줄", extract_tunnel_url(f"\x1b[36m{good}\x1b[0m") == good, "")

    print("\n[자식 환경]")
    run = tmp / "run-x"
    dry = child_env_overrides("dry", None, run, "/m")
    ok &= _check("dry 카카오4 · NCP2 전부 빈 문자열", all(k in dry and dry[k] == "" for k in SILENCED_KEYS), f"{len(SILENCED_KEYS)}키")
    ok &= _check("dry DB · 캡처 = 실행 폴더 안", dry[ENV_DB] == f"sqlite:///{run}/ddingdong.db"
                 and Path(dry[ENV_CAPTURE_DIR]).parent == run, "")
    ok &= _check("dry 캡처 URL = 로컬 라우트", dry[ENV_CAPTURE_URL_BASE] == CAPTURE_ROUTE, "")
    shell = {k: "" for k in SILENCED_KEYS}   # 셸에 빈 값이 남아 있는 최악의 경우
    for base in ("https://a-b.trycloudflare.com", "https://a-b.trycloudflare.com/"):
        live = child_env_overrides("live", base, run, "/m")
        ok &= _check(f"live 캡처 URL{' (끝 /)' if base.endswith('/') else ''}",
                     live[ENV_CAPTURE_URL_BASE] == "https://a-b.trycloudflare.com/captures", "슬래시 중복 없음")
    ok &= _check("live 6키 덮지 않음(문자열 주입 0)", all(live.get(k) is None for k in SILENCED_KEYS), "")
    ok &= _check("live 셸 빈 값 제거 → .env 가 이김", not any(k in apply_overrides(shell, live) for k in SILENCED_KEYS), "")
    ok &= _check("dry 적용 결과 6키 빈 값", all(apply_overrides({k: "x" for k in SILENCED_KEYS}, dry)[k] == ""
                                              for k in SILENCED_KEYS), "")
    try:
        child_env_overrides("live", None, run, "/m")
        ok &= _check("live 터널 없음 거부", False, "통과해 버림")
    except ValueError:
        ok &= _check("live 터널 없음 거부", True, "")

    print("\n[.env 읽기]")
    env_text = ("# 주석\n\nDEVICE_TOKEN=dev1\nDASHBOARD_TOKEN=old-first\n"
                f"export DASHBOARD_TOKEN=\"{secret}\"  # 끝 주석\nKAKAO_REFRESH_TOKEN='{secret}'\n"
                "PLAIN=a b # c\nNOEQ\nEMPTY=\nBAD=\"open\nINTERP=${HOME}\n")
    parsed = parse_env_text(env_text)
    ok &= _check("중복 키 = 마지막 줄", effective_value("DASHBOARD_TOKEN", env_text, {}) == secret, "값 비교만")
    ok &= _check("따옴표 · 주석 · 빈 값", (parsed["PLAIN"], parsed["EMPTY"], parsed["NOEQ"]) == ("a b", "", None), "")
    ok &= _check("범위 밖 = 실패로 드러냄", parsed["BAD"] is UNSUPPORTED and parsed["INTERP"] is UNSUPPORTED, "")
    ok &= _check("이미 있는 환경 변수가 이김", effective_value("DASHBOARD_TOKEN", env_text, {"DASHBOARD_TOKEN": "sh"}) == "sh", "")
    try:
        import dotenv   # 설치돼 있으면 실물 파서와 대조(값은 비교만)
        ref = dotenv.dotenv_values(stream=io.StringIO(env_text.replace("BAD=\"open\nINTERP=${HOME}\n", "")))
        mine = {k: v for k, v in parsed.items() if v is not UNSUPPORTED}
        ok &= _check("python-dotenv 실물과 일치", dict(ref) == mine, f"{len(ref)}키")
    except ImportError:
        print("  [SKIP] python-dotenv 미설치 — 실물 대조 생략")
    rows = token_key_rows(env_text, {})
    print(format_rows(rows))
    ok &= _check("토큰 키 점검 = 있음", [r[0] for r in rows] == ["✅", "✅"], "")
    ok &= _check("빈 토큰 = ❌", token_key_rows("DEVICE_TOKEN=\nDASHBOARD_TOKEN=x\n", {})[0][0] == "❌", "")

    print("\n[LISTEN · 실모델 · log-dir]")
    ok &= _check("lsof 빈 출력 = 빔", not listen_busy(""), "")
    ok &= _check("lsof 행 = 바쁨", listen_busy("COMMAND PID USER\npython3 1 u 3u IPv4 TCP *:5000 (LISTEN)\n"), "")
    ok &= _check("실모델 통과(실측 자릿수)", real_model_ok(461_280, 54), "461,280 KB · 54")
    ok &= _check("mock 거부(RSS · TF 미달)", not real_model_ok(60_000, 0), "")
    ok &= _check("TF 0 거부(RSS 커도)", not real_model_ok(500_000, 0), "")
    ok &= _check("RSS 미달 거부(TF 있어도)", not real_model_ok(120_000, 54), "")
    inside = REPO_ROOT / "server" / "demo_up_should_not_exist"
    for raw, want in ((str(inside), False), (str(REPO_ROOT), False), (str(tmp / "x"), True)):
        try:
            got = validate_log_dir(raw) == Path(raw).resolve()
        except Fail:
            got = False
        ok &= _check(f"log-dir {'repo 밖 허용' if want else 'repo 안 거부'}", got == want and not inside.exists(), Path(raw).name)
    link = tmp / "link_to_repo"
    link.symlink_to(REPO_ROOT / "server")
    try:
        validate_log_dir(str(link / "x"))
        ok &= _check("심볼릭 링크로 repo 안 거부", False, "통과해 버림")
    except Fail:
        ok &= _check("심볼릭 링크로 repo 안 거부", True, "")

    print("\n[서버 로그 거르기]")
    post = '127.0.0.1 - - [01/Jan/2026 00:00:00] "\x1b[1m\x1b[31mPOST /api/v1/detect HTTP/1.1\x1b[0m" 401 -'
    ok &= _check("POST (ANSI 포함) 표시", server_line_shown(post), "")
    ok &= _check("폴링 GET 숨김", not server_line_shown('127.0.0.1 - - [x] "GET /api/v1/stats?period=today HTTP/1.1" 200 -'), "")
    ok &= _check("WARNING · Traceback 표시", server_line_shown("[x] WARNING in routes: kakao token status")
                 and server_line_shown("Traceback (most recent call last):"), "")

    print("\n[상태 판정]")
    h = {"device_status": "offline", "kakao_token_status": "expired", "kakao_token_expires_in_minutes": 0,
         "clova_api_status": "degraded"}
    reg = {"state": "none", "collected": 0}
    ok &= _check("dry 기대 = 통과", judge_health("dry", h, reg)[1], "")
    ok &= _check("dry 토큰 행 있음 = 실패", not judge_health("dry", dict(h, kakao_token_status="valid", kakao_token_expires_in_minutes=300), reg)[1], "")
    ok &= _check("dry Clova ok = 실패", not judge_health("dry", dict(h, clova_api_status="ok"), reg)[1], "")
    ok &= _check("live 만료 = ⚠️(멈추지 않음)", judge_health("live", h, reg)[1], "")

    print("\n[요약 파일]")
    summary = tmp / "summary.txt"
    summary.write_text(format_rows(rows + judge_health("dry", h, reg)[0]), encoding="utf-8")
    ok &= _check("요약 파일에 시크릿 없음", secret not in summary.read_text(encoding="utf-8"), "")
    return ok


def _raise_interrupt(_signum, _frame):
    raise KeyboardInterrupt


def main(argv=None):
    ap = argparse.ArgumentParser(description="시연 기동 도구 (터널 · 실모델 서버 · 대시보드)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--self-test", action="store_true", help="임시 디렉터리에서 자기검증(포트 · 네트워크 · 자식 0)")
    ap.add_argument("--mode", choices=("live", "dry"), help="live = 부스 · 리허설 / dry = 보드 실측(카톡 · CSR 0) — 필수")
    ap.add_argument("--model-path", help="inference_savedmodel 폴더 — 필수")
    ap.add_argument("--log-dir", help="로그 · 요약 폴더(repo 밖, 안에 run-* 를 만든다) — 필수")
    ap.add_argument("--port", type=int, help="서버 포트 — 필수")
    ap.add_argument("--dashboard", action="store_true", help="npm run dev 도 띄운다")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    missing = [f"--{k.replace('_', '-')}" for k in ("mode", "model_path", "log_dir", "port") if getattr(args, k) is None]
    if missing:
        ap.error(f"필수 인자 누락: {' '.join(missing)} (기본값 없음)")   # argparse 종료 코드 = 2
    # SIGTERM · SIGHUP(터미널 닫힘)도 Ctrl+C 와 같은 정리 경로로. SIGINT 도 명시한다 — `&` · nohup 로 띄우면
    # 셸이 SIGINT 를 무시 상태로 물려주고 파이썬은 그 상태를 유지해 Ctrl+C 정리가 안 탄다(스모크 실측).
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, _raise_interrupt)
    try:
        return main_run(args)
    except Fail as exc:   # 실행 폴더를 만들기 전의 인자 실패
        print(f"❌ {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
