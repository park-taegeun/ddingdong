#!/usr/bin/env python3
"""PreToolUse 훅: 비밀값 파일(secrets.h, .env*)을 Claude 도구가 건드리지 못하게 막는다.

허용 예외: *.template, .env.example
입력: Claude Code가 stdin으로 넘기는 훅 JSON. 차단 시 exit 2 + stderr에 이유.
자체 점검: python3 .claude/hooks/block-secrets.py --selftest
"""
import json
import re
import sys

# 앞뒤가 파일명 문자([\w.-])가 아닌 자리의 secrets.h / .env* 토큰
SECRET = re.compile(r"(?<![\w.-])(secrets\.h|\.env[\w.-]*)(?![\w.-])")
FIELDS = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "MultiEdit": ("file_path",),
    "Grep": ("path", "glob"),
    "Bash": ("command",),
}


def blocked_names(text):
    return [m for m in SECRET.findall(text)
            if not m.endswith(".template") and m != ".env.example"]


def check(event):
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    for field in FIELDS.get(tool, ()):
        hits = blocked_names(str(tool_input.get(field) or ""))
        if hits:
            return f"{tool}.{field}에 비밀값 파일({', '.join(sorted(set(hits)))})이 있어 차단합니다."
    return None


def selftest():
    def ev(tool, **kw):
        return {"tool_name": tool, "tool_input": kw}

    blocked = [
        ev("Read", file_path="/repo/firmware/include/secrets.h"),
        ev("Edit", file_path="/repo/.env"),
        ev("Write", file_path="server/.env.local"),
        ev("MultiEdit", file_path=".env.bak"),
        ev("Grep", pattern="KEY", path="/repo/.env"),
        ev("Grep", pattern="KEY", glob=".env*"),
        ev("Bash", command="cd firmware/include && cat secrets.h"),
        ev("Bash", command="cat .env|head"),
        ev("Bash", command="cp .env.example .env"),
    ]
    allowed = [
        ev("Read", file_path="/repo/firmware/include/secrets.h.template"),
        ev("Read", file_path="/repo/.env.example"),
        ev("Edit", file_path="/repo/.gitignore"),
        ev("Grep", pattern=r"\.env", path="/repo/server"),
        ev("Bash", command="python3 -c 'import os; print(os.environ)'"),
        ev("Bash", command="ls server/venv/bin"),
        ev("Glob", pattern="**/.env"),  # 검문 대상 아님
    ]
    for e in blocked:
        assert check(e), f"차단돼야 함: {e}"
    for e in allowed:
        assert not check(e), f"허용돼야 함: {e}"


def main():
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        print("selftest ok")
        return 0
    try:
        event = json.load(sys.stdin)
    except ValueError as e:
        print(f"block-secrets: 훅 입력 JSON 파싱 실패 — 안전하게 차단합니다: {e}", file=sys.stderr)
        return 2
    reason = check(event)
    if reason:
        print(f"{reason} (허용 예외: *.template, .env.example)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
