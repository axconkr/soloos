# SoloOS

> **The AI-Native Operating System for Solopreneur CEOs.**  
> 1인 대표가 10명 몫 실행을 가능케 하는 오픈소스 조직 운영체제.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/Status-Build_Phase-orange.svg)](./docs/ARCHITECTURE.md)
[![Sprint](https://img.shields.io/badge/Sprint-Week_1_of_6-blue.svg)](./docs/SPRINT_PLAN_6WEEKS.md)

---

## Why SoloOS

솔로프리너 CEO는 하루에 마케팅·세일즈·운영·재무·CS·프로덕트 결정을 전부 내린다.  
**Zapier로는 부족하고, CRM으로는 좁고, 챗봇으로는 얕다.**

SoloOS는 이 6개 영역을 **AI 에이전트 팀**이 실행하고, CEO는 **결재만** 하도록 설계된 운영체제다.

- 🧠 **6개 코어 모듈**: Command Deck · Agent Roster · Workflow Engine · Memory Cortex · Revenue Loop · Ledger & Metrics
- 🛂 **결재 우선 (Human Gate)**: 돈·외부 커뮤니케이션·비가역 액션은 항상 CEO 확인
- 📜 **감사 가능 (Auditable)**: 모든 자동 액션이 JSONL append-only 로그로 남음
- 🔌 **Hermes 위에 얹은 얇은 레이어**: 스킬·크론·게이트웨이·메모리 재사용
- 📱 **Telegram-first UX**: 대화가 곧 태스크가 곧 KPI

---

## Status

**Phase:** MVP Build (Week 1 of 6)  
**Timeline:** 2026-07-01 → 2026-08-11  
**Dogfood:** Phillip의 회사 [ax-con.com](https://ax-con.com)에서 실사용 중

---

## Documentation

| Doc | 내용 |
|-----|------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 6개 모듈, 계층 구조, 데이터 흐름, 확정 기술결정 5개 |
| [SPRINT_PLAN_6WEEKS.md](./docs/SPRINT_PLAN_6WEEKS.md) | 주차별 목표·산출물·검수 기준 |
| [DATA_MODEL.md](./docs/DATA_MODEL.md) | SQLite 스키마, 벡터 저장, 파일 레이아웃 |
| [POLICY_ENGINE.md](./docs/POLICY_ENGINE.md) | 결재 규칙, 가드레일, 오버라이드 |
| [MODULE_SPEC/M1_COMMAND_DECK.md](./docs/MODULE_SPEC/M1_COMMAND_DECK.md) | 첫 모듈 상세 스펙 |
| [AGENT_OPERATING_CONSTITUTION.md](./docs/AGENT_OPERATING_CONSTITUTION.md) | SoloOS 공통 에이전트 운영 규칙: CEO-readable, evidence-first, TDD, decision gates |
| [AI_COMPANY_STACK_V0_1.md](./docs/AI_COMPANY_STACK_V0_1.md) | Phillip 개인 적용용 7부서 AI Company Stack: 후보 스킬 감사, 권한, 도입 기준 |
| [DEPARTMENT_PLAYBOOKS.md](./docs/DEPARTMENT_PLAYBOOKS.md) | CEO Office·Engineering·Design·Growth·Finance·Legal·Ops 라우팅/핸드오프 규칙 |
| [STITCH_AGENT_WORKFLOW.md](./docs/STITCH_AGENT_WORKFLOW.md) | Google Stitch + stitch-skills 디자인→코드 워크플로우와 검증 기준 |
| [OPENMANUS_REFERENCE_ANALYSIS.md](./docs/OPENMANUS_REFERENCE_ANALYSIS.md) | OpenManus 구조/UX 패턴 참고 분석: 직접 복제 금지, 라이선스 리스크, 한국어 CEO cockpit 변환 기준 |
| [.stitch/DESIGN.md](./.stitch/DESIGN.md) | AX Consulting Mission Control 디자인 토큰/가이드: Stitch 및 coding agent 공통 기준 |

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/<org>/soloos && cd soloos

# 2. Install dev/runtime dependencies
uv sync --extra dev

# 3. Configure optional secrets
cp .env.example .env  # Telegram token, Anthropic key, Google OAuth 등

# 4. Migrate DB
uv run soloos db migrate

# 5. Preflight
uv run soloos doctor

# 6. Seed the M2 Agent Roster
uv run soloos agents seed
uv run soloos agents list

# 7. Command Deck smoke path
uv run soloos deck dispatch "안녕" --platform telegram --chat-id <your-chat-id>
uv run soloos deck dispatch "이번 주 블로그 3편 초안 만들어줘" --platform telegram --chat-id <your-chat-id>
uv run soloos actions next
uv run soloos actions run-one
uv run soloos workflows list
uv run soloos workflows steps WF-0001
uv run soloos workflows run-step WF-0001
uv run soloos workflows run-step WF-0001
uv run soloos workflows run-step WF-0001
# failed step이 있으면:
uv run soloos workflows retry-step WF-0001 WS-0001
uv run soloos audit search --action-type workflow_step_run
uv run soloos audit show STEP-WS-0001
uv run soloos deck status
uv run soloos deck queue
uv run soloos deck brief
```

현재 Week 1 smoke path는 CLI 기반 Command Deck입니다. Telegram gateway 연결 전에도 자연어 입력 → intent 저장 → session 갱신 → `actions` pending 큐 적재 → Agent Roster 조회 → `content_plan` workflow 생성(`workflows` + `workflow_steps`) → step executor 실행(`pending → running → success/failed`) → `AgentRunner` 인터페이스 호출(현재 기본값: deterministic fallback) → `data/workspace/content/WF-*/WS-*.md` 파일 산출물 생성 및 `output_ref=file://...` 저장 → `workflow_step_run` audit event 기록 → 모든 step 완료 시 workflow `success` 또는 step 실패 시 workflow `failed` → `retry-step`으로 failed step 재큐잉 → action/audit 기록까지 검증할 수 있습니다.

### Visual dashboard smoke

```bash
cd apps/web
npm install
npm run verify
npm run dev
# open http://127.0.0.1:3000 (or the port Next prints if 3000 is occupied)
```

`apps/web`는 AX Consulting용 Mission Control UI입니다. `apps/web/public/soloos-snapshot.json`을 통해 SQLite runtime snapshot을 읽고, 첫 화면은 CEO가 바로 이해할 수 있도록 “한 줄 결론 / 방금 끝난 일 / 다음에 볼 것 / 필립 승인 필요 / AI 직원 현황”으로 번역합니다. 상세 action/workflow/audit 정보는 “상세 로그 보기” 뒤에 둡니다.

Branding note: repo 안에 명확한 Phillip/AX Consulting 로고 asset이 아직 없습니다. Mission Control header와 deployment 문서에는 `TODO: brand asset required` blocker를 표시했습니다. 공개 production deploy 전 CEO가 공식 로고/favicon asset과 사용 규칙을 제공·승인해야 합니다.

### OpenRouter live runner

SoloOS는 OpenRouter를 별도 runner로 지원합니다. OpenRouter 키가 있는 환경에서는 다음처럼 켭니다.

```bash
export SOLOOS_AGENT_RUNNER=openrouter
export OPENROUTER_API_KEY="..."
export SOLOOS_OPENROUTER_MODEL="openai/gpt-5-mini"  # 원하는 OpenRouter model slug
uv run soloos workflows run-step WF-0001
```

OpenRouter runner는 OpenAI SDK의 chat-completions 호환 API를 `https://openrouter.ai/api/v1`로 호출하고, 실패하면 deterministic fallback으로 audit warning을 남깁니다.

---

## Architecture at a Glance

```
CEO ──chat──▶ Command Deck ──▶ Agent Roster (7 agents)
                    │                │
                    ▼                ▼
              Approval Queue    Workflow Engine
                    │                │
                    ▼                ▼
              Audit Log ◀─────── Executor
                                     │
              ┌──────────────────────┼────────────────────┐
              ▼                      ▼                    ▼
        Memory Cortex          Revenue Loop         Ledger & Metrics
        (sqlite-vec)          (deals, invoices)    (daily briefing)
```

---

## Design Principles

1. **CEO decides, agents execute** — 결재 → 실행 → 검증 3단
2. **Conversation is the task** — Telegram 대화가 곧 CRM 레코드
3. **Agents are teammates, not tools** — 역할·권한·KPI 명시
4. **Observability first** — 감사 로그 없으면 액션 없음
5. **Local first, cloud optional** — self-host 가능해야 함
6. **Boring tech, sharp seams** — 검증된 컴포넌트 + 명확한 인터페이스

---

## Business Model

**Open-source core + consulting/adoption services** (Sentry / PostHog 모델).

- Core: MIT 오픈소스, self-host free
- Services: 도입 컨설팅, 커스텀 에이전트 개발, managed hosting (예정)

---

## Contributing

MVP 완성 (Week 6) 후 공개 기여 오픈 예정.  
지금은 dogfood + 사양 검증 단계입니다.

---

## License

MIT © 2026 Phillip Hong / ax-con.com
