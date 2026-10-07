"""decisions.md 구조 인식 청커 — 순수 함수(네트워크 · 파일 I/O 0).

입력 = 원문 텍스트 + 커밋 해시 + 설정 dict. 출력 = Chunk 목록.
모든 청크는 원문 줄의 조각(span = 줄 번호 · 시작 열 · 끝 열)으로만 만들어지므로
「비어 있지 않은 모든 줄이 어떤 청크에 들어간다」는 span 합집합으로 검사할 수 있다.
"""
import hashlib
import re
from dataclasses import dataclass, field

CHUNKER_VERSION = "1"

HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$")
SUBSECTION_RE = re.compile(r"^\*\*\(([A-Za-z]{1,2}(?:-\d+)?)\)\s*(.*?)(?:\*\*|$)")
SECTION_NUM_RE = re.compile(r"^(\d+(?:\.\d+)+)\s")       # 6.2 · 33.30 · 17.1.1 (5/12 같은 날짜는 제외)
CATEGORY_RE = re.compile(r"^카테고리\s+(\d+)\s*:")
LIST_RE = re.compile(r"^(?:[-*]|\d+\.)\s")
NESTED_LIST_RE = re.compile(r"^\s+(?:[-*]|\d+\.)\s")
FENCE_RE = re.compile(r"^\s*```")
SENTENCE_END_RE = re.compile(r"(?<=[.!?。])\s+")
STRIKE_RE = re.compile(r"~~(.+?)~~")
PR_RE = re.compile(r"(?<![\w&/])#(\d{1,4})\b")
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")

REQUIRED_KEYS = ("chunk_target_chars", "chunk_max_chars", "overlap_chars", "mark_superseded")


@dataclass
class Chunk:
    spans: list            # [(줄 번호 1-기반, 시작 열, 끝 열)]
    heading_path: list     # 제목 문자열 목록(바깥 → 안)
    section: str
    display: str = ""      # 표시 원문(원문 그대로)
    body: str = ""         # 임베딩 · 답변용 본문(mark_superseded 켜면 취소선 치환)
    embed_text: str = ""   # 제목 경로 줄 + 본문
    meta: dict = field(default_factory=dict)


def require_keys(config, keys):
    missing = [k for k in keys if k not in config]
    if missing:
        raise ValueError(f"설정에 값이 없다(기본값 금지): {', '.join(missing)}")


def mark_superseded(text):
    return STRIKE_RE.sub(lambda m: f"[폐기] {m.group(1)} [/폐기]", text)


def _span_text(lines, spans):
    return "\n".join(lines[n - 1][s:e] for n, s, e in spans)


def _size(lines, spans):
    return len(_span_text(lines, spans))


def _full(lines, n):
    return (n, 0, len(lines[n - 1]))


def _sentence_pieces(lines, n, target, overlap):
    """한 줄을 문장 경계에서 target 안팎으로 자른다. 두 번째 조각부터 앞 조각 끝 약 overlap자를 겹친다.
    문장 하나가 target을 넘으면 그 문장은 쪼개지 않는다(쪼갤 수 없는 단위)."""
    text = lines[n - 1]
    ends = [m.start() for m in SENTENCE_END_RE.finditer(text) if m.end() < len(text)] + [len(text)]
    pieces, start, end = [], 0, 0
    for b in ends:
        if end > start and b - start > target:
            pieces.append([(n, start, end)])
            k = text.find(" ", max(end - overlap, start), end)   # 겹침 시작을 단어 경계에 맞춘다
            start = k + 1 if k != -1 else max(end - overlap, start)
        end = b
    pieces.append([(n, start, end)])
    return pieces


def _pack(lines, pieces, target):
    """조각(각각 span 목록)을 순서대로 target 이하로 묶는다. 조각 하나가 넘으면 그대로 둔다."""
    out, cur = [], []
    for p in pieces:
        if cur and _size(lines, cur + p) > target:
            out.append(cur)
            cur = []
        cur = cur + p
    if cur:
        out.append(cur)
    return out


def _split_lines(lines, spans, cfg):
    """여러 줄 단위 → 줄 단위, 그래도 넘는 한 줄 → 문장 단위."""
    pieces = []
    for sp in spans:
        if _size(lines, [sp]) > cfg["chunk_max_chars"]:
            pieces.extend(_sentence_pieces(lines, sp[0], cfg["chunk_target_chars"], cfg["overlap_chars"]))
        else:
            pieces.append([sp])
    return pieces


def _split_unit(lines, kind, spans, cfg):
    """크기 초과 단위를 쪼갠 조각 목록(각각 span 목록)을 돌려준다."""
    if _size(lines, spans) <= cfg["chunk_max_chars"]:
        return [spans]
    target = cfg["chunk_target_chars"]
    if kind == "table" and len(spans) > 2:
        head, rows = spans[:2], spans[2:]
        groups = _pack(lines, [[r] for r in rows], target - _size(lines, head))
        return [head + g for g in groups]
    if kind == "list":
        segs, cur = [], []
        for sp in spans:
            if cur and NESTED_LIST_RE.match(lines[sp[0] - 1]):
                segs.append(cur)
                cur = []
            cur.append(sp)
        segs.append(cur)
        pieces = []
        for seg in segs:
            if _size(lines, seg) > cfg["chunk_max_chars"]:
                pieces.extend(_split_lines(lines, seg, cfg))
            else:
                pieces.append(seg)
        return pieces
    return _split_lines(lines, spans, cfg)


def _units(lines):
    """(종류, span 목록, 제목 경로, 절) 단위를 원문 순서대로 낸다. 제목 줄 자체도 단위다."""
    path = []          # [(레벨, 제목 문자열, 절 이름)]
    sub = None         # (소절 문자, 제목)
    i, n_lines = 0, len(lines)

    def cur_path():
        p = [t for _, t, _ in path]
        if sub:
            p.append(f"({sub[0]}) {sub[1]}".strip())
        return p

    def cur_section():
        if not path:
            return "(머리말)"
        sec = path[-1][2]
        return f"{sec}({sub[0]})" if sub else sec

    while i < n_lines:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        start = i
        if FENCE_RE.match(line):
            i += 1
            while i < n_lines and not FENCE_RE.match(lines[i]):
                i += 1
            i = min(i + 1, n_lines)
            kind = "code"
        elif HEADING_RE.match(line):
            level, title = len(HEADING_RE.match(line).group(1)), HEADING_RE.match(line).group(2).strip()
            path = [p for p in path if p[0] < level]
            m_num, m_cat = SECTION_NUM_RE.match(title), CATEGORY_RE.match(title)
            name = m_num.group(1) if m_num else (m_cat.group(1) if m_cat else title)
            path.append((level, title, name))
            sub = None
            i += 1
            kind = "heading"
        elif SUBSECTION_RE.match(line):
            m = SUBSECTION_RE.match(line)
            sub = (m.group(1), m.group(2).strip())
            i += 1
            while i < n_lines and lines[i].strip() and lines[i][0].isspace():
                i += 1
            kind = "para"
        elif line.startswith("|"):
            while i < n_lines and lines[i].startswith("|"):
                i += 1
            kind = "table"
        elif line.startswith(">"):
            while i < n_lines and lines[i].startswith(">"):
                i += 1
            kind = "quote"
        elif LIST_RE.match(line):
            i += 1
            while i < n_lines and lines[i].strip() and lines[i][0].isspace():
                i += 1
            kind = "list"
        else:
            i += 1
            while i < n_lines and lines[i].strip() and not _starts_block(lines[i]):
                i += 1
            kind = "para"
        spans = [_full(lines, k + 1) for k in range(start, i) if lines[k].strip()]
        yield kind, spans, cur_path(), cur_section()


def _starts_block(line):
    return bool(FENCE_RE.match(line) or HEADING_RE.match(line) or SUBSECTION_RE.match(line)
                or line.startswith("|") or line.startswith(">") or LIST_RE.match(line))


def chunk(text, commit, config):
    require_keys(config, REQUIRED_KEYS)
    lines = text.split("\n")
    target = config["chunk_target_chars"]
    groups = []   # (span 목록, 제목 경로, 절)
    cur, cur_key = [], None
    for kind, spans, hpath, section in _units(lines):
        key = (tuple(hpath), section)
        for piece in _split_unit(lines, kind, spans, config):
            if cur and (key != cur_key or _size(lines, cur + piece) > target):
                groups.append((cur, list(cur_key[0]), cur_key[1]))
                cur = []
            cur, cur_key = cur + piece, key
    if cur:
        groups.append((cur, list(cur_key[0]), cur_key[1]))

    chunks = []
    for spans, hpath, section in groups:
        display = _span_text(lines, spans)
        body = mark_superseded(display) if config["mark_superseded"] else display
        path_line = " > ".join(hpath) if hpath else "(머리말)"
        embed_text = f"{path_line}\n{body}"
        c = Chunk(spans=spans, heading_path=hpath, section=section,
                  display=display, body=body, embed_text=embed_text)
        c.meta = {
            "commit": commit,
            "section": section,
            "heading_path": path_line,
            "line_start": min(s[0] for s in spans),
            "line_end": max(s[0] for s in spans),
            "pr_numbers": ",".join(sorted(set(PR_RE.findall(display)), key=int)),
            "dates": ",".join(sorted(set(DATE_RE.findall(display)))),
            "has_strikethrough": bool(STRIKE_RE.search(display)),
            "chunk_hash": hashlib.sha256(embed_text.encode("utf-8")).hexdigest()[:16],
        }
        chunks.append(c)
    return chunks


def count_oversized_units(text, config):
    """chunk_max_chars를 넘어 쪼개기 대상이 된 단위 수."""
    lines = text.split("\n")
    return sum(_size(lines, spans) > config["chunk_max_chars"] for _, spans, _, _ in _units(lines))


def uncovered_lines(text, chunks):
    """span 합집합이 덮지 못한 비공백 문자가 있는 줄 번호 목록(커버리지 불변식)."""
    lines = text.split("\n")
    covered = {}
    for c in chunks:
        for n, s, e in c.spans:
            covered.setdefault(n, []).append((s, e))
    bad = []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        mask = [False] * len(line)
        for s, e in covered.get(n, []):
            for k in range(s, e):
                mask[k] = True
        if any(ch.strip() and not mask[k] for k, ch in enumerate(line)):
            bad.append(n)
    return bad
