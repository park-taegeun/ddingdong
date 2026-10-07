# decisions-rag MCP 시연 기록

Claude Code에서 질문 1개를 던져 Claude가 decisions-rag 도구로 답한 대화를 세션 기록 파일(`*.jsonl`)에서 스크립트로 그대로 뽑은 것이다.

- 날짜: 2026-10-07 16:48 (Asia/Seoul)
- Claude Code 2.1.291 · 모델 `claude-opus-5-5`
- 서버 기동 인자(공개분): `--commit e471052` · `--config tools/decisions-rag/configs/baseline.json` · `--persist-dir`는 repo 밖 인덱스(경로 비공개). 등록 = 사용자 범위(`claude mcp add --scope user`)
- 도구 호출: decisions-rag 2회(`search_decisions` 1 · `get_section` 1) + Claude Code 도구 스키마 불러오기(`ToolSearch`) 1회
- 추출: 스크립트로 기록 파일을 JSON 파싱해 뽑았다. 손 편집 0. 각 블록은 기록 원문과 바이트 대조를 통과했다(호출 입력 · `ToolSearch` 결과는 기록의 JSON 표기 그대로, 나머지는 문자열 그대로).
- 뺀 것: 시스템 메시지 · 사고(thinking) 블록 · 첨부 · 메타데이터(작업 폴더 · 경로 · 세션 id · 토큰 수) · tool_use의 `caller` 필드 · 같은 세션의 다른 작업
- **결과는 힌트다** — 인용 전에 원문(`git show e471052:docs/decisions.md`)과 대조한다. 아래 「근거 줄 대조」가 그 대조다.
- 평가셋 확인: 이 질문은 평가셋 v1(30) · H1(15) 문항이 아니다 — 공백 정규화 완전 일치 0 · 글자 3-gram Jaccard 최고 0.051. README 시운전 질문 3개 중 「카카오 비즈 앱」 질문을 바꿔 말한 꼴이다(질문 문장 0.484 · 메시지 전체 0.192). 시운전 질문은 평가셋에 넣지 않는 질문이다.

## 대화

### 1. 질문

```text
decisions-rag 도구만 써서 답해 줘. 카카오 알림을 보낼 때 비즈 앱 심사를 피한 이유가 뭐야? 근거 절과 줄 번호도 같이 적어 줘.
```

### 2. 호출 — `ToolSearch`

```json
{"query":"select:mcp__decisions-rag__search_decisions,mcp__decisions-rag__get_section,mcp__decisions-rag__list_sections","max_results":3}
```

### 3. 결과 — `ToolSearch`

```json
[{"type":"tool_reference","tool_name":"mcp__decisions-rag__search_decisions"},{"type":"tool_reference","tool_name":"mcp__decisions-rag__get_section"},{"type":"tool_reference","tool_name":"mcp__decisions-rag__list_sections"}]
```

### 4. 호출 — `mcp__decisions-rag__search_decisions`

```json
{"query":"카카오 알림 비즈 앱 심사 회피 이유","k":6}
```

### 5. 결과 — `mcp__decisions-rag__search_decisions`

```json
{"result":"{\n \"commit\": \"e471052\",\n \"config\": \"baseline\",\n \"embedder\": \"openai\",\n \"results\": [\n  {\n   \"rank\": 1,\n   \"score\": 0.4149,\n   \"section\": \"30.3\",\n   \"heading_path\": \"카테고리 30: 외부 계정 셋업 SSoT (2026-05-13 신설, 2026-05-16 NCP 추가) > 30.3 카카오 비즈 앱 회피 결정 근거\",\n   \"ref\": \"e471052@L3797-L3804\",\n   \"text\": \"### 30.3 카카오 비즈 앱 회피 결정 근거\\n- **채택**: 개인 개발자 계정 + talk_message \\\"선택 동의\\\" / **회피**: 비즈 앱 심사 (사업자 등록증 필요)\\n- **근거**:\\n  1. 시스템 흐름상 \\\"나에게 보내기\\\" (memo API)만 사용 → 비즈 앱 불필요 (카테고리 7 일치)\\n  2. 본인이 본인 계정에 동의하는 구조 → \\\"선택 동의\\\"로 충분\\n  3. \\\"이용 중 동의\\\" 대비 \\\"선택 동의\\\"가 더 단순 (카카오 로그인 시 동의 받음)\\n- **출처**: 카카오 디벨로퍼스 공식 문서 (talk_message scope 동의 항목 정책)\"\n  },\n  {\n   \"rank\": 2,\n   \"score\": 0.3846,\n   \"section\": \"7.5(c)\",\n   \"heading_path\": \"카테고리 7: STT + 알림 > 7.5 A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 토큰 재발급 실무 확정 (2026-09-03 PoC-(39) 신설, PR #40 `70aea1d`) > (c) ★ 카카오 REST API 키 rotate = 유령 미결 확정 (근거유형 = 실측 화면 catch, 학습 21 계열)\",\n   \"ref\": \"e471052@L1265-L1271\",\n   \"text\": \"**(c) ★ 카카오 REST API 키 rotate = 유령 미결 확정 (근거유형 = 실측 화면 catch, 학습 21 계열)**\\n- 2026-07-31 노출 이후 이월돼 있던 \\\"REST키·client_secret rotate\\\" 항목. ⚠️ **decisions.md 미등재**(Notion DB3 전용 추적 항목).\\n- 실화면 catch: 플랫폼 키 카드 ⋮ 메뉴 = 수정 / 복제 키 생성뿐(삭제·재발급 없음). 수정 페이지 = 리다이렉트 URI / 클라이언트 시크릿 / 추가 정보뿐, 키 값 재발급 항목 부재.\\n- 즉 노출된 REST API 키를 무효화할 방법이 콘솔에 없다 — rotate는 애초 **실행 불가능한 작업**이었다.\\n- 대안 = client_secret 재발급으로 토큰 교환 관문 복원(재발급일 2026-09-03).\\n- 위협 평가(근거유형 = **논증**): REST키 단독으로는 memo 발송 불가 — 인가 코드는 등록된 Redirect URI로만 전달, 토큰 교환에 client_secret 필수, 사용자 본인 동의 필요, memo는 토큰 소유자 본인에게만 발송.\\n- 기각한 대안: 호출 허용 IP 설정(카카오 공식 권고) — 부스가 모바일 핫스팟(카테고리 23)이라 IP 가변, 적용 시 데모 파손.\"\n  },\n  {\n   \"rank\": 3,\n   \"score\": 0.3747,\n   \"section\": \"7.5(f)\",\n   \"heading_path\": \"카테고리 7: STT + 알림 > 7.5 A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 토큰 재발급 실무 확정 (2026-09-03 PoC-(39) 신설, PR #40 `70aea1d`) > (f) ★ 데스크톱 vs 모바일 렌더 차이 — 카피 조정 불요 판정 (근거유형 = 실측 화면 catch)\",\n   \"ref\": \"e471052@L1311-L1318\",\n   \"text\": \"**(f) ★ 데스크톱 vs 모바일 렌더 차이 — 카피 조정 불요 판정 (근거유형 = 실측 화면 catch)**\\n- 데스크톱 카카오톡에서 확정 카피 ②의 어절이 줄 끝에서 분절되는 현상 관측(예: \\\"천/으로\\\", \\\"음/성통화\\\").\\n- 5060 노안 사용자 가독성 우려로 줄바꿈 조정을 검토했으나, 휴대폰 카카오톡 실화면 확인 결과 분절 미발생 → 조치 불요로 판정.\\n- 원칙: 렌더 결과는 클라이언트 폭에 종속된다. 실사용 환경(모바일)을 확인하지 않고 데스크톱 화면만 보고 카피를 손대면 7.1 검증본을 훼손하게 된다.\\n- 🆕 **[등재 — 관찰 2026-09-15 PoC-(49)] 1차 텍스트 알림 2행 「모바일에서 확인해 주세요.」의 출처**\\n  - **[실측]** 저장소 코드에 해당 문구 **0건**이다 — `server/` · `dashboard/src/` 전수 grep. **대조군**으로 같은 grep에서 「초인종이 울렸」 **2건**이 생존했다(도구 사망 아님).\\n  - **[실측]** `_post_memo`가 보내는 payload 실물 키 = `{object_type: \\\"text\\\", text, link: {web_url, mobile_web_url}}` — **`button_title` 키는 없다.**\\n  - **[가능성 — 미실증]** 2행과 앱 버튼 「Ddingdong」은 **카카오 클라이언트가 `link`로부터 만들어 내는 기본 렌더**일 가능성이 있다. **확정하지 말 것.**\"\n  },\n  {\n   \"rank\": 4,\n   \"score\": 0.3689,\n   \"section\": \"7.5(j)\",\n   \"heading_path\": \"카테고리 7: STT + 알림 > 7.5 A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 토큰 재발급 실무 확정 (2026-09-03 PoC-(39) 신설, PR #40 `70aea1d`) > (j) 🆕 카카오 커밋 안전 가드 `_assert_commit_is_safe` — SSoT 틈 등재 (발견 2026-09-26 PoC-(60) / 반영 2026-09-27, 근거유형 = 코드 docstring 명시(`server/app/kakao.py`) + 실측 `git log -S`)\",\n   \"ref\": \"e471052@L1342-L1343\",\n   \"text\": \"**(j) 🆕 카카오 커밋 안전 가드 `_assert_commit_is_safe` — SSoT 틈 등재 (발견 2026-09-26 PoC-(60) / 반영 2026-09-27, 근거유형 = 코드 docstring 명시(`server/app/kakao.py`) + 실측 `git log -S`)**\\n- **사실 (docstring 요약)**: 카카오 계층은 토큰을 갱신할 때 commit한다. 그 commit에 **남의 변경이 딸려가지 않도록**, 세션에 `KakaoToken` 외 클래스의 미커밋 변경이 있으면 **`RuntimeError`**를 낸다 — docstring 규약 「Notification 생성 이전에만 호출」을 실행 시점에 강제하는 가드다. `KakaoTokenError`가 아닌 이유 = 호출부의 `except KakaoTokenError`에 잡혀 카카오 발송 실패로 조용히 둔갑하면 버그가 숨는다.\"\n  },\n  {\n   \"rank\": 5,\n   \"score\": 0.3622,\n   \"section\": \"7.5(d)\",\n   \"heading_path\": \"카테고리 7: STT + 알림 > 7.5 A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 토큰 재발급 실무 확정 (2026-09-03 PoC-(39) 신설, PR #40 `70aea1d`) > (d) ★ 카카오 콘솔 경로 정정 (근거유형 = 실측 화면 catch, 학습 13 화면 우선)\",\n   \"ref\": \"e471052@L1273-L1277\",\n   \"text\": \"**(d) ★ 카카오 콘솔 경로 정정 (근거유형 = 실측 화면 catch, 학습 13 화면 우선)**\\n- client_secret 위치 실측: 앱 설정 → 플랫폼 키 → REST API 키 카드 → [클라이언트 시크릿] 칩(URL 패턴 `/console/app/{appId}/config/platform-key/rest/{keyId}`).\\n- 콘솔이 멀티 REST 키 구조로 개편됨(+ REST API 키 추가 / 복제 키 생성 존재). 클라이언트 시크릿은 REST 키에 종속, 키 발급 시 기본 활성화.\\n- REST API 키 생성 일시 = 2026-05-14(카테고리 30.2 외부 계정 셋업일과 정합).\\n- ⚠️ 본 세션에서 AI가 콘솔 경로·기능 유무를 3회 연속 오안내(① REST키 재발급 UI 부재 추정→오류 ② 시크릿 위치→오류 ③ rotate 가능 판단→오류), 2026-09-02 NCP 콘솔 경로 오안내에 이은 연속. → **원칙: AI가 제시한 외부 콘솔 경로·기능 유무는 화면 catch 전까지 전부 추정.**\"\n  },\n  {\n   \"rank\": 6,\n   \"score\": 0.3619,\n   \"section\": \"7.5(e)\",\n   \"heading_path\": \"카테고리 7: STT + 알림 > 7.5 A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 토큰 재발급 실무 확정 (2026-09-03 PoC-(39) 신설, PR #40 `70aea1d`) > (e) ★ 카카오 OAuth refresh 토큰 부트스트랩 절차 확정 (근거유형 = 실측)\",\n   \"ref\": \"e471052@L1301-L1305\",\n   \"text\": \"  - **P1** = `doorbell` **1.0** · `tof_check.passed=false` · `skip_reason=\\\"tof_rejected\\\"` · **`primary_sent=false`** ⇒ **발송을 시도하지 않은 호출은 갱신을 유발하지 않는다**(S0 = S1).\\n  - **P2** = **`primary_sent=true`** · `primary_sent_at` **2026-09-15T17:04:18.922+09:00** ⇒ **갱신은 P2 호출에서 일어났다.** 새 access의 TTL = **21,600초(6시간)**.\\n  - **P2 이후 첫 폴링에서 만료 WARNING이 사라졌다** — DB 상태와 **독립적인 경로**로 「만료 상태 탈출」이 재확인된다(8.5(d) 연동).\\n  - **도착 확인 (근거유형 = 실측 화면 catch)**: **PC 카카오톡과 모바일 카카오톡에서 동일하게 표시**됐다 — 1행 「🔔[띵동] 초인종이 울렸어요.」 + 2행 「모바일에서 확인해 주세요.」 + 앱 버튼 「Ddingdong」. 도착 시각 **17:04 KST**. 2행의 출처 = **(f)** 참조.\\n  - 🆕 **위 (e)의 「`updated_at`이 실발송 세션과 같은 날이나 인과는 미실증」이 본 회차에서 닫혔다** — **같은 호출(P2) 안에서 `primary_sent=true`와 `updated_at` 이동이 함께 관측**됐기 때문이다. ⚠️ **닫힌 것은 「발송이 갱신을 돌렸는가」뿐**이고 **「refresh가 재발급됐는가」는 여전히 미확인**이다.\"\n  }\n ],\n \"note\": \"검색 결과는 힌트 — 인용 전에 원문(docs/decisions.md@커밋)과 대조할 것\"\n}"}
```

### 6. 호출 — `mcp__decisions-rag__get_section`

```json
{"section":"30.3","offset":0}
```

### 7. 결과 — `mcp__decisions-rag__get_section`

```json
{"result":"{\n \"commit\": \"e471052\",\n \"config\": \"baseline\",\n \"section\": \"30.3\",\n \"total\": 1,\n \"offset\": 0,\n \"next_offset\": null,\n \"chunks\": [\n  {\n   \"section\": \"30.3\",\n   \"heading_path\": \"카테고리 30: 외부 계정 셋업 SSoT (2026-05-13 신설, 2026-05-16 NCP 추가) > 30.3 카카오 비즈 앱 회피 결정 근거\",\n   \"ref\": \"e471052@L3797-L3804\",\n   \"text\": \"### 30.3 카카오 비즈 앱 회피 결정 근거\\n- **채택**: 개인 개발자 계정 + talk_message \\\"선택 동의\\\" / **회피**: 비즈 앱 심사 (사업자 등록증 필요)\\n- **근거**:\\n  1. 시스템 흐름상 \\\"나에게 보내기\\\" (memo API)만 사용 → 비즈 앱 불필요 (카테고리 7 일치)\\n  2. 본인이 본인 계정에 동의하는 구조 → \\\"선택 동의\\\"로 충분\\n  3. \\\"이용 중 동의\\\" 대비 \\\"선택 동의\\\"가 더 단순 (카카오 로그인 시 동의 받음)\\n- **출처**: 카카오 디벨로퍼스 공식 문서 (talk_message scope 동의 항목 정책)\"\n  }\n ],\n \"note\": \"검색 결과는 힌트 — 인용 전에 원문(docs/decisions.md@커밋)과 대조할 것\"\n}"}
```

### 8. 답

```markdown
decisions-rag 도구로만 확인한 내용입니다.

**근거 절: §30.3 「카카오 비즈 앱 회피 결정 근거」 (`docs/decisions.md` L3797–L3804, 인덱스 커밋 `e471052`)**

- **채택한 방식**: 개인 개발자 계정과 `talk_message` 「선택 동의」를 씁니다.
- **피한 것**: 비즈 앱 심사입니다. 이 심사에는 사업자 등록증이 필요합니다.

**피한 이유**
1. 시스템은 「나에게 보내기」(memo API)만 씁니다. 그래서 비즈 앱이 필요 없습니다. 이 판단은 카테고리 7과도 맞습니다.
2. 사용자가 자기 계정의 발송에 직접 동의하는 구조여서 「선택 동의」만으로 충분합니다.
3. 「이용 중 동의」보다 「선택 동의」가 더 단순합니다. 카카오 로그인 때 동의를 함께 받기 때문입니다.

문서에 적힌 출처는 카카오 디벨로퍼스 공식 문서의 `talk_message` scope 동의 항목 정책입니다.

**참고할 점**
- 인덱스 커밋 `e471052`는 현재 HEAD `b1fbeab`와 다릅니다. 지시대로 원문 파일은 열지 않았으므로 줄 번호는 `e471052` 기준입니다. 그 뒤 문서가 바뀌었다면 현재 줄 번호는 다를 수 있습니다.
- 카테고리 7과 맞는다는 근거 1에 대해서는 검색 결과에 §7.5(c)가 함께 나왔습니다(L1265–L1271). memo는 토큰을 가진 본인에게만 발송된다는 내용입니다.
```

## 근거 줄 대조

결과 · 답의 근거 표기마다 `git show e471052:docs/decisions.md`의 그 줄 범위를 `common.mask_secrets`로 마스킹한 원문과 비교했다. 결과 본문이 그 범위 안에 그대로 들어 있으면 「일치」, 범위의 빈 줄을 뺀 뒤 들어 있으면 「일치(빈 줄 제외)」(청커가 빈 줄을 청크에 넣지 않는다 — `chunker.py`). 답의 표기는 같은 절 라벨 · 같은 줄 범위의 결과 청크가 있는지와 그 청크의 대조 결과를 따른다.

| 표기 | 출처 | 일치 |
|---|---|---|
| `e471052@L3797-L3804` | search_decisions | 일치(빈 줄 제외) |
| `e471052@L1265-L1271` | search_decisions | 일치 |
| `e471052@L1311-L1318` | search_decisions | 일치 |
| `e471052@L1342-L1343` | search_decisions | 일치 |
| `e471052@L1273-L1277` | search_decisions | 일치 |
| `e471052@L1301-L1305` | search_decisions | 일치 |
| `e471052@L3797-L3804` | get_section | 일치(빈 줄 제외) |
| `§30.3 L3797–L3804` | 답 | 일치(빈 줄 제외) |
| `§7.5(c) L1265–L1271` | 답 | 일치 |
