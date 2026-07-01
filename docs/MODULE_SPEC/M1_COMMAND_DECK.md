# M1 — Command Deck (Spec v0.1)

**Role in SoloOS:** CEO의 유일한 입력 관문. 자연어 지시를 받아 라우팅하고, 상태·결재·브리핑을 되돌려준다.

---

## 1. Responsibilities

| # | 책임 | 산출물 |
|---|------|--------|
| R1 | Intent 분류 & 라우팅 | `{intent, agent_id, params}` |
| R2 | Approval Queue 관리 | Pending / Approved / Rejected / Expired |
| R3 | 상태 요약 브리핑 | On-demand + 일일 07:00 자동 |
| R4 | CEO ↔ Agents 대화 세션 유지 | Session state (KV) |
| R5 | 결재 인터랙션 UX | Telegram inline buttons |

**Non-goals (M1):** 에이전트 실행 로직 자체(M2), 워크플로우 오케스트레이션(M3), 메모리 저장(M4).

---

## 2. Interfaces

### 2.1 Inbound (사용자 → SoloOS)
- **Telegram**: 자연어 텍스트, 명령 (`/deck ...`), 인라인 버튼 콜백
- **Discord**: 텔레그램과 동등 기능 (보조)
- **Voice**: STT → 텔레그램 텍스트 파이프 재사용

### 2.2 Outbound (SoloOS → 사용자)
- Telegram 메시지 (Markdown, 인라인 키보드)
- Google Docs/Sheets 링크
- 감사 로그 참조 ID (`#A-NNNN`)

### 2.3 Downstream (Command Deck → 다른 모듈)
```
CommandDeck.dispatch(intent) → M2.AgentRoster.get(agent_id)
                            → M3.Workflow.enqueue(task)
CommandDeck.brief()          → M6.Ledger.summary_for(day|week)
CommandDeck.recall(query)    → M4.Memory.search(query)
```

---

## 3. Commands

### 3.1 자연어 지시 (Freeform)
- 아무 텍스트 → Intent Classifier (Reasoning tier LLM) → 라우팅
- 예: "이번 주 블로그 3편 초안" → `intent=content_plan, agent=cmo`

### 3.2 슬래시 명령 (Explicit)

| 명령 | 동작 |
|------|------|
| `/deck` | 도움말 + 오늘 요약 |
| `/deck status` | 현재 실행 중 태스크, 결재 대기, 이슈 |
| `/deck queue` | 결재 대기 목록 (인라인 버튼 포함) |
| `/deck brief [today\|week]` | 브리핑 즉시 발송 |
| `/deck recall <query>` | Memory Cortex 검색 |
| `/deck agents` | 활성 에이전트 목록 + 상태 |
| `/deck use=<model> <text>` | 특정 모델 강제 (예: `use=opus`) |
| `/deck pause <agent>` | 특정 에이전트 일시 중지 |
| `/deck resume <agent>` | 재개 |
| `/deck audit <id>` | 감사 로그 조회 |

---

## 4. Data Model

```sql
-- SQLite: data/deck.sqlite

CREATE TABLE approvals (
  id TEXT PRIMARY KEY,                -- 'AP-0088'
  created_at INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  action_type TEXT NOT NULL,          -- publish_content, spend_money, etc.
  target TEXT NOT NULL,               -- resource ref
  preview_url TEXT,                   -- Google Doc / Sheet link
  cost_krw INTEGER DEFAULT 0,
  risk TEXT CHECK(risk IN ('LOW','MED','HIGH')) DEFAULT 'LOW',
  policy_rule TEXT,                   -- rule id from policy engine
  status TEXT CHECK(status IN ('pending','approved','rejected','deferred','expired')) DEFAULT 'pending',
  decided_at INTEGER,
  decided_by TEXT,                    -- 'ceo' or 'auto'
  comment TEXT,
  audit_id TEXT                       -- link to audit log
);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_created ON approvals(created_at);

CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,             -- 'telegram' | 'discord'
  chat_id TEXT NOT NULL,
  thread_id TEXT,
  active_agent TEXT,
  context_snapshot TEXT,              -- JSON: {last_intent, entities, ...}
  updated_at INTEGER
);

CREATE TABLE intents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  session_id TEXT,
  raw_text TEXT NOT NULL,
  classified_intent TEXT,
  routed_to TEXT,                     -- agent_id
  confidence REAL,
  latency_ms INTEGER
);
```

---

## 5. Intent Classifier

**Tier:** Reasoning (Claude Sonnet 4)  
**Prompt strategy:** Few-shot, 15 canonical examples, structured output (JSON).

```json
{
  "intent": "content_plan",
  "agent_id": "cmo",
  "confidence": 0.92,
  "params": {"topic_count": 3, "type": "blog", "period": "this_week"},
  "requires_clarification": false,
  "clarification_question": null
}
```

**Fallback:** confidence < 0.6 → 필립에게 명확화 질문 반환 ("CMO/Sales/Ops 중 어느 쪽으로 갈까요?").

**Cache:** identical raw_text within 5 min → skip LLM call.

---

## 6. Approval Interaction Flow

```
Agent (M2) → Workflow (M3) → Policy Gate
                                │
                                ▼
                        [needs approval]
                                │
                                ▼
                    CommandDeck.request_approval()
                                │
                                ├─► approvals table INSERT (status=pending)
                                ├─► JSONL audit line
                                └─► Telegram message + inline buttons
                                            │
                                     [user clicks]
                                            ▼
                        webhook → CommandDeck.decide(id, verdict)
                                │
                                ├─► approvals UPDATE
                                ├─► JSONL audit line
                                └─► Workflow.resume(id) or Workflow.abort(id)
```

### 6.1 Inline Button Payload
```
callback_data = "ap:{id}:{verdict}"
verdict ∈ {approve, reject, defer, comment}
```

### 6.2 Timeouts
- 24h no response → 재알림 (bump)
- 72h no response → auto-expire, log, notify

---

## 7. Briefing Generator

### 7.1 On-demand (`/deck brief`)
- Query M6.Ledger for last 24h stats
- Query approvals for pending count
- Query M4.Memory for "yesterday's decisions" summary
- Render Telegram-friendly Markdown

### 7.2 Scheduled (Daily 07:00 KST)
- Hermes cron entry: `soloos.deck.morning_brief`
- Same generator, formatted for daybreak

---

## 8. Session State

Persisted in SQLite (`sessions` table) + in-process cache.

**Session key:** `{platform}:{chat_id}:{thread_id}`  
**Retention:** 7 days idle → archive to Memory Cortex.

---

## 9. Observability

- Every dispatch → intent row + audit line
- Metric: intent classification latency p50/p95, approval turnaround time, LLM cost per session
- Exported to Mission Control (existing) via daily job.

---

## 10. File Layout (Hermes plugin structure)

```
soloos/
  plugins/
    command_deck/
      manifest.yaml
      handlers/
        telegram.py
        discord.py
      classifier/
        prompt.md
        examples.jsonl
      approvals/
        service.py
        schema.sql
      briefing/
        generator.py
        templates/
          morning.md.j2
          weekly.md.j2
      commands/
        deck_status.py
        deck_queue.py
        deck_brief.py
        deck_recall.py
        deck_agents.py
        deck_audit.py
      tests/
        test_classifier.py
        test_approvals.py
```

---

## 11. Implementation Order (Week 1)

1. Day 1: repo skeleton + manifest + `/deck status` (stub)
2. Day 2: approvals schema + inline button roundtrip (dummy action)
3. Day 3: intent classifier + routing table (agents 미구현이어도 dispatch stub)
4. Day 4: briefing generator (M6 미구현 → 하드코딩 데이터로 형식만)
5. Day 5: session state + audit log integration + E2E dry run
6. Day 6-7: 실제 필립 dogfood 사용, 버그 픽스, docs

---

## 12. Acceptance Criteria (Week 1 End)

- [ ] 필립이 텔레그램에 "안녕" 입력 → 정상 응답 (classifier fallback)
- [ ] `/deck status` → 결재 대기/실행 중 요약 3초 이내
- [ ] 결재 요청 → 인라인 버튼 클릭 → status DB 갱신 + audit log 기록
- [ ] `/deck brief today` → 모형 브리핑 렌더링
- [ ] 24h 미응답 시 재알림 발송
- [ ] 모든 액션 `data/audit/YYYY-MM-DD.jsonl`에 기록
