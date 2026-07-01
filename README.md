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

---

## Quickstart (준비 중)

```bash
# 1. Clone
git clone https://github.com/<org>/soloos && cd soloos

# 2. Install
uv venv && source .venv/bin/activate
uv pip install -e .

# 3. Configure
cp .env.example .env  # Telegram token, Anthropic key, Google OAuth 등

# 4. Migrate DB
soloos db migrate

# 5. Run
soloos start
```

10분 안에 자기 텔레그램에서 `/deck status` 응답을 볼 수 있는 것이 목표입니다.

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
