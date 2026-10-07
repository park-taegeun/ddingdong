"""index.py · query.py 공용 — 설정 · 커밋 고정 원문 · 경로 가드 · 비밀값 점검 · manifest."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent

CONFIG_KEYS = (
    "name", "chunk_target_chars", "chunk_max_chars", "overlap_chars", "mark_superseded",
    "embed_model", "embed_price_usd_per_1m_tokens", "max_embed_tokens", "top_k", "answer_model",
)

# 비밀값 · 개인정보 형태. md5 같은 일반 16진 해시는 여기에 걸리지 않는다(접두어 · 도메인이 필요).
SECRET_PATTERNS = {
    "openai_key": re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "quick_tunnel": re.compile(r"\b[a-z0-9-]+\.trycloudflare\.com\b"),
    # 개인정보 — 인덱싱은 막지 않고 인덱스 본문에서만 가린다.
    "customs_id": re.compile(r"\bP\d{12}\b"),                      # 개인통관고유번호
    # @ 뒤 첫 글자 = 영문: pkg@1.2.3.tgz 같은 패키지 버전 문자열을 메일로 보지 않는다.
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
    "aws_account_id": re.compile(r"(?<=Account ID `)\d{12}(?=`)"),
    "mobile_phone": re.compile(r"\b01[016789]-\d{3,4}-\d{4}\b"),
}
# 이 종류가 나오면 인덱싱을 멈춘다(터널 주소는 마스킹만 하고 진행).
BLOCKING_SECRETS = ("openai_key", "bearer_token")


def fail(msg, code=2):
    print(f"오류: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    missing = [k for k in CONFIG_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"설정에 값이 없다(기본값 금지): {', '.join(missing)}")
    unknown = sorted(set(cfg) - set(CONFIG_KEYS))
    if unknown:
        raise ValueError(f"알 수 없는 설정 키: {', '.join(unknown)}")
    return cfg


def config_hash(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def repo_root():
    out = subprocess.run(["git", "-C", str(TOOL_DIR), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=True)
    return Path(out.stdout.strip()).resolve()


def resolve_commit(commit):
    out = subprocess.run(["git", "-C", str(TOOL_DIR), "rev-parse", "--verify", f"{commit}^{{commit}}"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise ValueError(f"커밋을 찾을 수 없다: {commit}")
    return out.stdout.strip()


def read_doc_at(commit):
    """작업 트리가 아니라 커밋에 고정된 docs/decisions.md를 읽는다."""
    out = subprocess.run(["git", "-C", str(TOOL_DIR), "show", f"{commit}:docs/decisions.md"],
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8")


def check_outside_repo(path):
    """심볼릭 링크를 푼 실제 경로가 repo 안이면 거부한다."""
    real = Path(os.path.realpath(os.path.expanduser(path)))
    root = repo_root()
    if real == root or root in real.parents:
        raise ValueError(f"repo 안 경로는 쓸 수 없다(repo 밖만 허용): {path}")
    return real


def scan_secrets(text):
    """{종류: [줄 번호, ...]} — 값 자체는 돌려주지 않는다."""
    found = {k: [] for k in SECRET_PATTERNS}
    for n, line in enumerate(text.split("\n"), 1):
        for kind, pat in SECRET_PATTERNS.items():
            found[kind].extend([n] * len(pat.findall(line)))
    return found


def mask_secrets(text):
    for kind, pat in SECRET_PATTERNS.items():
        text = pat.sub(f"[MASKED:{kind}]", text)
    return text


def package_versions():
    from importlib.metadata import version
    names = ("llama-index-core", "llama-index-vector-stores-chroma", "llama-index-embeddings-openai",
             "llama-index-llms-openai", "chromadb", "openai", "tiktoken")
    return {n: version(n) for n in names}


def openai_key():
    """tools/decisions-rag/.env의 OPENAI_API_KEY. 없으면 None(호출부가 친절히 종료)."""
    from dotenv import dotenv_values
    env = TOOL_DIR / ".env"
    return dotenv_values(env).get("OPENAI_API_KEY") if env.exists() else None


def chroma_client(persist_dir):
    import chromadb
    from chromadb.config import Settings
    # 익명 통계 끄기(설치 버전의 Posthog.capture는 이미 no-op이지만 설정으로도 끈다).
    return chromadb.PersistentClient(path=str(persist_dir), settings=Settings(anonymized_telemetry=False))


def use_bundled_tiktoken_cache():
    """tiktoken이 인코딩 파일을 내려받지 않도록 llama-index-core에 동봉된 캐시를 가리킨다."""
    import llama_index.core
    os.environ["TIKTOKEN_CACHE_DIR"] = str(Path(llama_index.core.__file__).parent / "_static" / "tiktoken_cache")


COLLECTION = "decisions"
MANIFEST = "manifest.json"
