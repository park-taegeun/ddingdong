#!/usr/bin/env python3
"""tls_probe_server — upload_spike_tls 하네스 전용 TLS transport 프로브 서버 (7/29, 카테고리 6.2).

목적: ESP32 WiFiClientSecure의 [TCP → TLS 1.2 핸드셰이크 → 64KB multipart POST] 왕복
상대역. 실 /detect의 auth/idempotency/multipart 파싱은 복제하지 않는다(F9 — transport
전용). cert = ECDSA P-256 self-signed 자동 생성 → 프로덕션 Let's Encrypt ECDSA
P-256(카테고리 6.1)과 동일 키 타입이라 핸드셰이크 서버 서명 연산의 위상이 같다.

실행 (ESP32와 같은 핫스팟에 붙은 노트북에서):
    python3 firmware/tools/tls_probe_server.py
    # LAN IP 확인: ipconfig getifaddr en0  →  secrets.h의 SPIKE_TLS_SERVER_HOST에 기입

동작 노트:
- 펌웨어의 평문 TCP 프로브(F2 — 접속만 하고 close)는 TLS 핸드셰이크 EOF로 끝난다.
  ssl.SSLError는 OSError 서브클래스라 BaseServer가 조용히 drop — 에러 로그 없음이 정상.
- 응답 = 200 고정(실 /detect의 201과 구분 — 이 서버가 실서버가 아님을 코드 레벨로 표시).
- cert/key는 certs/ 하위 자동 생성(.gitignore 대상, openssl 필요 — macOS 기본 포함).
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

CERT_BASENAME = "tls_probe_cert.pem"
KEY_BASENAME = "tls_probe_key.pem"


def ensure_ecdsa_certs(certs_dir: str) -> tuple[str, str]:
    """ECDSA P-256 self-signed cert/key가 없으면 openssl로 생성 후 경로 반환."""
    os.makedirs(certs_dir, exist_ok=True)
    cert_path = os.path.join(certs_dir, CERT_BASENAME)
    key_path = os.path.join(certs_dir, KEY_BASENAME)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    print(f"[CERT] ECDSA P-256 self-signed cert 생성 중 → {certs_dir}/")
    subprocess.run(
        ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key_path],
        check=True,
    )
    subprocess.run(
        ["openssl", "req", "-new", "-x509", "-key", key_path, "-out", cert_path,
         "-days", "365", "-subj", "/CN=ddingdong-tls-probe"],
        check=True,
    )
    return cert_path, key_path


class ProbeHandler(BaseHTTPRequestHandler):
    # 왕복 최소화: 기본 HTTP/1.0 응답(Connection: close) 유지 — 펌웨어는 요청당 새 연결(콜드 측정).

    def do_POST(self):  # noqa: N802 (BaseHTTPRequestHandler 규약)
        t0 = time.monotonic()
        length = int(self.headers.get("Content-Length", 0))
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)
        read_ms = (time.monotonic() - t0) * 1000.0

        body = json.dumps({"ok": True, "bytes": length - remaining}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        # flush: 파일 리다이렉트 실행 시 블록 버퍼링으로 로그 유실 방지
        print(f"[PROBE] POST {self.path} client={self.client_address[0]} "
              f"bytes={length - remaining}/{length} read_ms={read_ms:.1f}", flush=True)

    def do_GET(self):  # noqa: N802 — 브라우저/curl 생존 확인용
        body = b'{"ok": true, "probe": "tls_probe_server"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 — 기본 stderr 로그 억제(자체 [PROBE] 라인 사용)
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="upload_spike_tls TLS transport 프로브 서버")
    parser.add_argument("--host", default="0.0.0.0", help="바인드 주소 (기본 0.0.0.0 — LAN 노출 필수)")
    parser.add_argument("--port", type=int, default=5001, help="포트 (기본 5001, secrets.h와 일치)")
    parser.add_argument("--certs-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs"))
    args = parser.parse_args()

    cert_path, key_path = ensure_ecdsa_certs(args.certs_dir)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2  # 클라이언트(mbedTLS 2.28.7)는 1.2 max → 1.2 협상
    ctx.load_cert_chain(cert_path, key_path)

    server = HTTPServer((args.host, args.port), ProbeHandler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print("[BOOT] tls_probe_server 기동")
    print(f"[BOOT]   bind={args.host}:{args.port}  cert={cert_path} (ECDSA P-256)")
    print(f"[BOOT]   python={sys.version.split()[0]}  {ssl.OPENSSL_VERSION}")
    print("[BOOT]   평문 TCP 프로브(무데이터 접속)는 조용히 drop됨 — 에러 로그 없음이 정상.")
    print("[BOOT]   종료 = Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BOOT] 종료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
