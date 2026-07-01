# SoloOS Architecture

> **The AI-Native Operating System for Solopreneur CEOs**  
> 1인 대표가 10명 몫 실행을 가능케 하는 조직 운영체제

**Version:** 0.2  
**Date:** 2026-07-01  
**Status:** Design Confirmed → Build Phase  
**License:** MIT

---

## 1. Vision & Principles

### 1.1 What SoloOS Is
솔로프리너 CEO 한 명이 **결정만 하면**, 다수의 AI 에이전트가 회사 운영 전 영역(마케팅·세일즈·운영·재무·CS·프로덕트)을 실행·측정·개선하는 **오픈소스 조직 운영체제**.

### 1.2 What SoloOS Is NOT
- ❌ 또 다른 AI 챗봇 래퍼
- ❌ Zapier 같은 범용 자동화 툴
- ❌ CRM/ERP 대체품 (오히려 감싸서 활용)
- ❌ 노코드 워크플로우 빌더

### 1.3 Design Principles

| # | 원칙 | 함의 |
|---|---|---|
| P1 | **CEO는 결정만, 실행은 에이전트가** | 모든 액션은 "결재 → 실행 → 검증" 3단 |
| P2 | **대화가 곧 태스크가 곧 KPI** | Telegram/Discord/음성이 1차 UI, 문서·지표는 자동 생성 |
| P3 | **팀 = 에이전트 페르소나 조합** | 에이전트는 툴이 아니라 "역할·권한·KPI를 가진 팀원" |
| P4 | **관찰가능성(Observability) 최우선** | 모든 자동 액션은 감사 로그, 롤백 가능, 알림 |
| P5 | **로컬 우선, 클라우드 선택** | dogfood 가능 self-host, SaaS는 옵션 |
| P6 | **Boring tech, sharp seams** | 이미 검증된 컴포넌트만, 인터페이스는 명확히 |

---

## 2. Six Core Modules (MVP)

```
┌──────────────────────────────────────────────────────────────┐
│                    CEO (Phillip / Solopreneur)                │
└─────────────────┬─────────────────────────────┬──────────────┘
                  │ 자연어 지시                   │ 결재 응답
                  ▼                             ▲
┌──────────────────────────────────────────────────────────────┐
│  [M1] COMMAND DECK  (Telegram / Discord / Web / Voice)       │
│  ─ 라우팅 · 결재 큐 · 상태 요약 · 브리핑                        │
└─────────────────┬────────────────────────────────────────────┘
                  │ intent + context
                  ▼
┌──────────────────────────────────────────────────────────────┐
│  [M2] AGENT ROSTER                                            │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌───────┐  │
│  │ CMO │ │Sales│ │ Ops │ │ Fin │ │ Prod│ │ CS  │ │Analyst│  │
│  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └───┬───┘  │
│     └───────┴───────┴───┬───┴───────┴───────┴────────┘      │
└─────────────────────────┼────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  [M3] WORKFLOW ENGINE                                         │
│  Trigger → Plan → Approval Gate → Execute → Verify → Notify  │
│  (Hermes cron + skills + gateway 기반)                        │
└─────┬──────────────────────┬────────────────────┬────────────┘
      │                      │                    │
      ▼                      ▼                    ▼
┌──────────────┐   ┌────────────────────┐  ┌──────────────────┐
│ [M4] MEMORY  │   │ [M5] REVENUE LOOP   │  │ [M6] LEDGER &    │
│    CORTEX    │◄──┤ Lead→Deal→Invoice   │  │     METRICS      │
│ 3-Layer      │   │ 대화형 CRM          │  │ 일일 브리핑·이상치│
│ (Vec+SQL+KV) │   │ 매출/현금흐름 예측  │  │ 주간 스코어카드   │
└──────┬───────┘   └──────────┬─────────┘  └────────┬─────────┘
       │                      │                     │
       └──────────────────────┼─────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│               EXTERNAL INTEGRATIONS (Adapters)                │
│  Gmail · GDrive · GDocs · Sheets · Stripe/Toss · Tally ·     │
│  Notion · Airtable · Slack · GitHub · Vercel · Cloudflare    │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 Module Responsibilities

| ID | 모듈 | 핵심 책임 | 주 사용자 인터페이스 |
|----|------|-----------|---------------------|
| **M1** | Command Deck | CEO 지시 라우팅, 결재 큐, 상태 요약 | Telegram/Discord/Web |
| **M2** | Agent Roster | 에이전트 페르소나·권한·KPI 관리 | Web 대시보드 |
| **M3** | Workflow Engine | 트리거·플래닝·실행·검증·롤백 | 이벤트/스케줄 자동 |
| **M4** | Memory Cortex | 개인/조직/프로젝트 3층 메모리, 검색 | 자동 (질의응답) |
| **M5** | Revenue Loop | 리드→계약→인보이스→회수 파이프라인 | 대화형 + 대시보드 |
| **M6** | Ledger & Metrics | 일일 브리핑, 스코어카드, 이상치 알림 | 아침 브리핑 + 대시 |

---

## 3. Layered Architecture

```
┌──────────────────────────────────────────────────────────┐
│  L5  Presentation    Telegram · Discord · Web · Voice    │
├──────────────────────────────────────────────────────────┤
│  L4  Modules         M1  M2  M3  M4  M5  M6              │
├──────────────────────────────────────────────────────────┤
│  L3  Core Services   Agent Runtime │ Policy │ Approval    │
│                      Event Bus     │ Audit  │ Scheduler   │
├──────────────────────────────────────────────────────────┤
│  L2  Platform        Hermes (skills · cron · gateway)    │
├──────────────────────────────────────────────────────────┤
│  L1  Data            SQLite (state) · Vector DB (memory) │
│                      Files (workspace) · KV (session)    │
├──────────────────────────────────────────────────────────┤
│  L0  Integrations    Adapters (Gmail, Stripe, GDocs...)  │
└──────────────────────────────────────────────────────────┘
```

- **L2 Hermes 활용점**: 스킬(에이전트 능력), 크론(스케줄), 게이트웨이(메시지 I/O), 메모리(세션)
- **L3 SoloOS 신규 서비스**: Policy Engine(결재 규칙), Approval Queue, Audit Log, Event Bus

---

## 4. Agent Roster (M2) 상세

### 4.1 기본 페르소나 7종

| 에이전트 | 미션 | 자동 권한 | 결재 필요 (Human Gate) |
|---------|------|-----------|----------------------|
| **CMO** | 콘텐츠·브랜드·수요 창출 | 초안 작성, 스케줄링 | 발행, 광고비 집행 |
| **Sales** | 리드 자격심사·제안·팔로업 | 이메일 초안, CRM 업데이트 | 계약 발송, 할인 |
| **Ops** | 태스크·프로세스·툴 관리 | 태스크 생성, 리마인더 | 툴 구독 변경, 외주 발주 |
| **Finance** | 인보이스·비용·캐시플로우 | 인보이스 초안, 리포트 | 지출, 세금 신고 |
| **Product** | 백로그·릴리즈·이슈 트리아지 | 이슈 라벨링, 문서화 | 릴리즈 결정, 기능 폐기 |
| **CS** | 고객 문의·온보딩·리텐션 | FAQ 응답, 티켓 라우팅 | 환불, 계약 변경 |
| **Analyst** | KPI 관측·이상치·리포트 | 일일 브리핑, 대시 갱신 | (전권 자동) |

### 4.2 에이전트 스펙 스키마 (예시)

```yaml
# agents/cmo.yaml
id: cmo
name: "CMO Agent"
mission: "브랜드 자산 축적과 유기적 수요 창출"
tone: "실용적, 데이터 기반, 과장 없음"
authority:
  auto:
    - draft_content
    - schedule_post
    - update_editorial_calendar
  requires_approval:
    - publish_content
    - spend_ads_budget
    - external_communication
kpi:
  weekly:
    - organic_reach
    - qualified_leads
    - content_output
escalation:
  - condition: "budget_overrun > 10%"
    to: finance
  - condition: "brand_risk_detected"
    to: ceo
skills: [content-writing, seo, ads-planning, editorial-calendar]
```

---

## 5. Workflow Engine (M3) 상세

### 5.1 실행 파이프라인

```
[Trigger]
  webhook | schedule | user_command | event
      │
      ▼
[Planner]
  goal → steps → tools → agents assignment
      │
      ▼
[Policy Gate] ◄── Policy Engine (rules.yaml)
  auto? / needs approval? / forbidden?
      │
      ├─ auto ────► [Executor]
      └─ approval ► [Approval Queue] ─► CEO 결재 ─► [Executor]
                                                          │
                                                          ▼
                                                    [Verifier]
                                                    tests / checks
                                                          │
                                          ┌───────────────┼───────────────┐
                                          ▼               ▼               ▼
                                      [Success]      [Rollback]      [Escalate]
                                          │               │               │
                                          └───────────────┴──────┬────────┘
                                                                 ▼
                                                          [Audit Log]
                                                          [Notify CEO]
```

### 5.2 Policy Engine 예시 규칙

```yaml
# policy/rules.yaml
rules:
  - id: money_out
    when: "action.type == 'payment' or action.type == 'subscription'"
    require: approval_from_ceo
    threshold_usd: 0  # 모든 지출은 결재

  - id: external_message
    when: "action.type == 'send_email' and action.audience == 'external'"
    require: approval_from_ceo
    exempt_if: "template.id in ['auto_receipt', 'auto_followup_v1']"

  - id: content_publish
    when: "action.type == 'publish' and channel in ['blog', 'twitter', 'linkedin']"
    require: approval_from_ceo

  - id: internal_ops
    when: "action.type in ['task_create', 'reminder', 'note_update']"
    require: none  # 자동
```

---

## 6. Memory Cortex (M4) 상세

### 6.1 3층 메모리 구조

```
┌────────────────────────────────────────────────────┐
│ Layer 1: PERSONAL     (CEO 개인 컨텍스트)          │
│  - 선호도, 의사결정 스타일, 관계, 캘린더            │
│  - Source: 대화, 프로필, 캘린더 이벤트              │
├────────────────────────────────────────────────────┤
│ Layer 2: ORGANIZATIONAL  (회사 지식)               │
│  - 미션·전략, 정책, 브랜드, 재무 상태, KPI          │
│  - Source: 문서, 회의록, 대시보드, 감사 로그        │
├────────────────────────────────────────────────────┤
│ Layer 3: PROJECT/CLIENT (프로젝트별 컨텍스트)      │
│  - 고객 히스토리, 제품 백로그, 실험 로그            │
│  - Source: CRM, 이슈트래커, 산출물, 대화 스레드     │
└────────────────────────────────────────────────────┘
```

### 6.2 저장소 구성

| 층 | 스토리지 | 이유 |
|----|---------|------|
| Structured facts | SQLite | 관계형·트랜잭션·백업 용이 |
| Semantic search | Vector DB (sqlite-vec 또는 chroma) | 로컬 우선, 임베딩 검색 |
| Session state | KV (Hermes 내장) | 짧은 컨텍스트, 빠른 접근 |
| Files/Docs | Workspace + Google Drive | 원본 + 협업 |

---

## 7. Revenue Loop (M5) 상세

### 7.1 파이프라인 단계

```
LEAD ──► QUALIFY ──► PROPOSAL ──► CONTRACT ──► INVOICE ──► COLLECT ──► RETAIN
  ▲         │           │            │            │           │           │
  │         ▼           ▼            ▼            ▼           ▼           ▼
Tally    Sales Q&A   자동 초안    e-sign      Stripe/     자동 리마인더  CS 온보딩
Form     스크립트    (CEO 결재)  (CEO 결재)   Toss                       + 업셀
```

### 7.2 대화형 CRM (Telegram-native)

```
CEO: "김이사님과 어제 통화한 거 기록해줘. 500만원 규모 관심."
  → Sales Agent가 파싱:
     - contact: 김이사 (기존 lead #L023)
     - stage: QUALIFY → PROPOSAL 이동
     - deal_size: 5,000,000 KRW
     - next_action: 제안서 초안 (자동 생성)
  → CEO에게 요약 + 제안서 초안 링크 반환
  → 3일 뒤 팔로업 자동 리마인더 셋업
```

---

## 8. Ledger & Metrics (M6) 상세

### 8.1 일일 아침 브리핑 (텔레그램 07:00)

```
📊 SoloOS Morning Brief · 2026-07-02

💰 매출
  어제: ₩1,240,000 (+18% WoW)
  이번 달 누계: ₩8,450,000 / 목표 ₩15M (56%)

🎯 파이프라인
  신규 리드: 3 (Tally 2, 소개 1)
  진행 중 딜: 7건 (₩45M 예상)
  이번 주 클로징 예정: 2건

⚠️ 알림
  · 광고비 어제 급증 (평균 3.2배) — 상세 보기
  · 인보이스 #INV-041 결제 지연 5일차

✅ 오늘의 결재 대기: 4건
  1. CMO: 블로그 발행 "AI Native Ops 3부"
  2. Sales: 김이사님 제안서 최종본
  3. Finance: SaaS 툴 갱신 ($49/mo × 3)
  4. Ops: 외주 디자이너 발주 (₩800,000)
```

### 8.2 Weekly Scorecard 자동 갱신
기존 `ops/WEEKLY_SCORECARD.md` 구조 재활용, 매주 월요일 08:00 자동 커밋.

---

## 9. Data Flow: 하나의 요청이 흐르는 방식

**시나리오**: CEO가 텔레그램에 "이번 주 블로그 3편 초안 잡아줘"

```
1. [L5 Telegram] 메시지 수신
       ▼
2. [M1 Command Deck] Intent 분류 → "content_planning" → CMO Agent 라우팅
       ▼
3. [M4 Memory Cortex] 컨텍스트 로드
       - 브랜드 톤 가이드 (조직층)
       - 최근 4주 발행물 (프로젝트층)
       - CEO 선호 (개인층)
       ▼
4. [M2 CMO Agent] 3개 주제 생성 + 개요 초안
       ▼
5. [M3 Workflow Engine] Policy 체크
       - 초안 생성: auto (Policy P1: draft 자동)
       - 발행: needs_approval
       ▼
6. [Executor] Google Docs 3개 생성 → 링크 반환
       ▼
7. [M6 Ledger] 태스크 카운트 +3, 콘텐츠 파이프라인 갱신
       ▼
8. [M1 Command Deck] CEO에게 결과 요약 + 링크 3개 + "발행 승인 대기"
```

**모든 단계는 Audit Log에 기록** → 언제 누가(어느 에이전트가) 무엇을 왜 했는지 재현 가능.

---

## 10. Non-Functional Requirements

| 카테고리 | 요구사항 |
|---------|---------|
| **응답성** | Command Deck 첫 응답 < 2초, 백그라운드 실행 알림 |
| **가용성** | Self-host 기준 99% (단일 노드 허용), SaaS는 99.9% |
| **보안** | 시크릿은 `.env` 또는 secret manager, PII 로그 마스킹 |
| **감사** | 모든 자동 액션 append-only log (JSONL), 30일 기본 보관 |
| **롤백** | 파괴적 액션(payment, publish, delete)은 사전 스냅샷 필수 |
| **확장** | 신규 에이전트/스킬은 YAML+MD 추가만으로 등록 |
| **관측** | Mission Control 대시보드 연동 (이미 시드 완료) |

---

## 11. Non-Goals (This Version)

- 다중 사용자/팀 협업 (SoloOS는 1인 CEO 전제)
- 자체 LLM 학습 (Claude/GPT/Gemini API 사용)
- 모바일 네이티브 앱 (Telegram으로 대체)
- 완전 무인 운영 (Human Gate는 원칙, 옵션 아님)
- 다국어 UI (한/영만 우선)

---

## 12. Confirmed Technical Decisions

| # | 항목 | 결정 | 근거 |
|---|------|------|------|
| **TD1** | Vector DB | **sqlite-vec** | 파일 1개 백업/이관, Hermes와 동일 SQLite 스택, 마이그레이션 여지 확보 |
| **TD2** | 결재 UI | **Telegram Inline Buttons** (Phase 1) + Web Dashboard (Phase 2 Week 4+) | 결재 latency 최소화, 필립 주 채널 |
| **TD3** | Audit Log | **JSONL append-only + SQLite index** | 불변성(파일) + 검색성(인덱스), 외부 반출 용이 |
| **TD4** | Web Stack | **Next.js 15 (App Router) + Tailwind + shadcn/ui + Vercel** | 기존 `ax.ax-con.com` 스택 재사용, 배포 자동화 |
| **TD5** | LLM Tiering | **3-Tier (Reasoning / Bulk / Embedding)** | 품질/비용 최적 배분 |

### 12.1 LLM Tier 배정표

| Tier | Model (Primary) | Fallback | 대상 에이전트/작업 |
|------|-----------------|----------|-------------------|
| **Reasoning** | `claude-sonnet-4` | `claude-opus-4` | CEO 브리핑, Sales 제안서, Product 결정, Policy 판정 |
| **Bulk** | `claude-haiku-4` | `gpt-4o-mini` | CS 응대, Ops 태스크, Analyst 리포트 초안, 콘텐츠 대량 생성 |
| **Embedding** | `text-embedding-3-small` (OpenAI) | `bge-small-en` (local) | Memory Cortex 벡터화, 의미 검색 |

**라우팅 규칙:** 각 에이전트 YAML에 `tier: reasoning|bulk` 명시 → Workflow Engine이 dispatch 시 선택. 사용자 강제 오버라이드 가능 (`/deck use=opus <task>`).

### 12.2 Telegram 결재 인터랙션 스펙 (초안)

```
📋 결재 요청 #A-0421
━━━━━━━━━━━━━━━━━━━━
에이전트: CMO
액션: publish_content
대상: 블로그 "AI Native Ops 3부"
비용: ₩0
리스크: LOW (브랜드 톤 검증 ✅)

📎 초안 미리보기: [Google Docs]
🔗 감사 로그: #A-0421

[ ✅ 승인 ] [ ❌ 거부 ] [ ⏸ 보류 ] [ 💬 코멘트 ]
```

- 응답 → Approval Queue 갱신 → Executor 트리거
- 미응답 24시간 → 에스컬레이션 (CEO에게 재알림)
- 미응답 72시간 → 자동 만료 + 감사 로그

### 12.3 Audit Log 스키마 (하이브리드)

**파일:** `data/audit/YYYY-MM-DD.jsonl` (append-only, daily rotation)

```jsonl
{"ts":"2026-07-01T09:12:33Z","id":"A-0421","actor":"agent:cmo","action":"draft_content","target":"blog:ai-native-ops-3","policy":"auto","cost_krw":0,"status":"success","hash":"sha256:..."}
{"ts":"2026-07-01T09:14:02Z","id":"A-0422","actor":"agent:cmo","action":"request_approval","target":"publish:blog:ai-native-ops-3","policy":"gate:content_publish","status":"pending","approval_id":"AP-0088"}
```

**인덱스:** `data/audit/index.sqlite` (검색용, 파일에서 재빌드 가능)
```sql
CREATE TABLE audit_index (
  id TEXT PRIMARY KEY,
  ts INTEGER NOT NULL,
  actor TEXT, action TEXT, target TEXT,
  status TEXT, policy TEXT, cost_krw INTEGER,
  file_path TEXT, line_offset INTEGER
);
CREATE INDEX idx_ts ON audit_index(ts);
CREATE INDEX idx_actor ON audit_index(actor);
```

---

## 13. Open Questions (Resolved in v0.2)

모든 v0.1 오픈 질문은 §12에서 확정됨. 새 결정 사항 발생 시 이 섹션에 추가.

---

## 14. Next Documents

- `docs/MODULE_SPEC/M1_COMMAND_DECK.md`
- `docs/MODULE_SPEC/M2_AGENT_ROSTER.md`
- `docs/MODULE_SPEC/M3_WORKFLOW_ENGINE.md`
- `docs/MODULE_SPEC/M4_MEMORY_CORTEX.md`
- `docs/MODULE_SPEC/M5_REVENUE_LOOP.md`
- `docs/MODULE_SPEC/M6_LEDGER_METRICS.md`
- `docs/SPRINT_PLAN_6WEEKS.md`
- `docs/DATA_MODEL.md`
- `docs/POLICY_ENGINE.md`

---

**End of Architecture v0.1**
