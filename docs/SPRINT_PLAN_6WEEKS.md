# SoloOS — 6-Week MVP Sprint Plan

**Owner:** Phillip (CEO) + Claude (build partner)  
**Duration:** 2026-07-01 → 2026-08-11 (6 weeks)  
**Goal:** MVP 6 modules working end-to-end on Phillip's own company (dogfood)

---

## Cadence

- **Daily**: 텔레그램 아침 브리핑 07:00 + 저녁 회고 21:00
- **Weekly**: 월요일 09:00 스프린트 킥오프 / 금요일 17:00 회고 + 데모
- **Approval Gates**: 모든 배포·비용 지출·외부 커뮤니케이션 필립 결재

---

## Week 1 (7/1–7/7) — Foundation & M1 Command Deck

**Theme:** 골격 세우기 + CEO가 대화하는 관문 확보

### Deliverables
- [ ] GitHub repo `soloos` 생성, MIT LICENSE, README, CONTRIBUTING
- [ ] 폴더 스캐폴딩 (Hermes 스킬 + 플러그인 구조)
- [ ] `M1 Command Deck` v0.1
  - Telegram intent 라우터 (자연어 → agent id)
  - 결재 큐 인메모리 → JSONL 영속화
  - `/deck status` `/deck queue` `/deck brief` 3개 명령
- [ ] Audit Log 파이프 (JSONL + sqlite 인덱스)
- [ ] 환경 설정: `.env.example`, secrets 검증 스크립트

### Definition of Done
- 필립이 텔레그램에 "오늘 뭐 있어?" → 3초 내 상태 요약 반환
- 결재 요청 인라인 버튼 → 응답 시 감사 로그 남음

---

## Week 2 (7/8–7/14) — M2 Agent Roster + M3 Workflow Engine

**Theme:** 에이전트 페르소나 등록 + 실행 파이프라인

### Deliverables
- [ ] 7종 에이전트 YAML 스펙 완성 (`agents/*.yaml`)
- [ ] Agent Runtime: YAML 로드 → 시스템 프롬프트 생성 → LLM 티어 라우팅
- [ ] Workflow Engine v0.1
  - Trigger sources: webhook, cron, user_command
  - Policy Gate: `policy/rules.yaml` 파싱 + 판정
  - Executor + Verifier (기본 성공 판정)
  - Rollback hook (파괴적 액션은 스냅샷 필수)
- [ ] LLM 티어 라우팅 (Reasoning / Bulk / Embedding)

### DoD
- `agent:cmo`가 "블로그 초안 3개" 자동 실행 → 결재 요청 → 승인 시 Google Docs 생성
- Audit log에 전 단계 기록

---

## Week 3 (7/15–7/21) — M4 Memory Cortex

**Theme:** 조직의 두뇌

### Deliverables
- [ ] sqlite-vec 설치 + 3층 스키마 (personal/org/project)
- [ ] Ingestion 파이프라인
  - Telegram/Discord 메시지 → 요약 → 임베딩 → 저장
  - Google Docs/Drive 신규 문서 → 인덱싱 (기존 OAuth 재활용)
  - Gmail 필터: `ax-con.com` 발신/수신 관련만
- [ ] Retrieval API: `memory.search(query, layer=[...], top_k=5)`
- [ ] 에이전트 컨텍스트 자동 주입 (Agent Runtime 통합)

### DoD
- "지난달 A고객이 뭐 요청했지?" → 3초 내 근거 3개 인용해서 답변
- 신규 문서 저장 후 5분 내 검색 가능

---

## Week 4 (7/22–7/28) — M5 Revenue Loop + Web Dashboard 착수

**Theme:** 매출 파이프라인 + 결재/감사 UI

### Deliverables
- [ ] Revenue Loop v0.1
  - Lead 소스: Tally 웹훅 (기존 leadwatch 크론 대체)
  - Stage 자동 전이 (`LEAD → QUALIFY → PROPOSAL → CONTRACT → INVOICE → COLLECT`)
  - 대화형 CRM: 텔레그램 문장 → 딜 업데이트 (Sales Agent)
  - Stripe/Toss 인보이스 어댑터 (초안, dry-run)
- [ ] Web Dashboard v0.1 (Next.js on Vercel)
  - `/dashboard` 결재 큐 (텔레그램과 실시간 동기화)
  - `/dashboard/audit` 감사 로그 검색
  - `/dashboard/pipeline` 파이프라인 칸반
  - 인증: 필립 이메일 매직링크 only

### DoD
- Tally 리드 제출 → 30초 내 텔레그램 알림 + Sales Agent 자격심사 초안
- 웹 대시보드에서 결재 승인 → 텔레그램에도 상태 반영

---

## Week 5 (7/29–8/4) — M6 Ledger & Metrics + Integration Hardening

**Theme:** 경영 계기판 + 실전 안정화

### Deliverables
- [ ] 일일 아침 브리핑 (07:00 Asia/Seoul)
  - 어제 매출/비용/리드/처리 태스크
  - 오늘 결재 대기 목록
  - 이상치 알림 (7일 이동평균 대비 ±2σ)
- [ ] Weekly Scorecard 자동 갱신 (`ops/WEEKLY_SCORECARD.md` 커밋)
- [ ] Analyst Agent 리포트 생성 (Google Sheets 대시보드 갱신)
- [ ] E2E 시나리오 3종 리허설:
  1. 콘텐츠: 아이디어 → 초안 → 결재 → 발행 → 성과 리포트
  2. 세일즈: Tally 리드 → 자격심사 → 제안 → 계약 → 인보이스
  3. 운영: CS 문의 → 라우팅 → 응답 초안 → 결재 → 발송

### DoD
- 3종 시나리오 각 1회 이상 실제 실행 성공
- 아침 브리핑 5일 연속 정상 발송

---

## Week 6 (8/5–8/11) — Documentation, Polish, Public Launch

**Theme:** 오픈소스 공개 준비 + 첫 대외 발표

### Deliverables
- [ ] `README.md` 완성 (5분 안에 이해되는 서사)
- [ ] `docs/QUICKSTART.md` (self-host 10분 안에 가동)
- [ ] `docs/ARCHITECTURE.md` v1.0 (현재 v0.2 → 실측 기반 정리)
- [ ] `docs/AGENT_COOKBOOK.md` (에이전트 커스터마이징 가이드)
- [ ] `docs/CASE_STUDY_PHILLIP.md` (dogfood 6주 결과, 숫자 근거 포함)
- [ ] 랜딩 페이지 `soloos.ax-con.com` (Next.js, Vercel)
- [ ] GitHub 공개 + Show HN / X / LinkedIn 런치 포스트
- [ ] 컨설팅 문의 폼 (Tally 재활용)

### DoD
- Repo public + Star 확보 목표 100+ (첫 주)
- 컨설팅 문의 3건 이상 유입 목표
- 필립이 부재중일 때도 SoloOS가 회사 절반 이상 자율 운영 (측정 지표: 결재 없이 완료된 태스크 비율 ≥ 40%)

---

## Risk Register

| 위험 | 확률 | 영향 | 대응 |
|-----|-----|------|-----|
| Hermes 종속으로 오픈소스 채택 저조 | 中 | 大 | Week 6에 Hermes-free adapter 문서화, 대안 러너블 예시 |
| LLM 비용 초과 (월 $500+) | 中 | 中 | 3-Tier 라우팅 + 일일 비용 알림 (Ledger 통합) |
| Tally/Stripe API 변경 | 低 | 中 | 어댑터 계층 격리, 통합 테스트 주 1회 |
| 필립 부재로 결재 병목 | 中 | 大 | 미응답 24h → 위임 규칙(pre-approved templates), 72h 자동 만료 |
| Dogfood 편향 (내 회사에만 최적) | 高 | 中 | Week 5에 외부 솔로프리너 2명 인터뷰, 가정 검증 |

---

## Weekly Checkpoint Template

매주 금요일 17:00 아래 포맷으로 자동 발송:

```
🏁 SoloOS Week N Recap

DONE ✅
- ...

MISSED ❌
- ... (사유 + 다음주 이관)

METRICS 📊
- 커밋: X, PR: Y, 자동 액션: Z
- 결재 요청/승인/거부: A/B/C
- LLM 비용: $D

NEXT WEEK 🎯
- 우선순위 3가지
```

---

## Post-MVP (Phase 2 예고)

- Content Factory / Client Vault / Vendor Ops / Compliance Guard / Learning Loop / Board Room
- 외부 파일럿 2–3명
- SaaS 매니지드 옵션 (Stripe 결제)
- 다국어 (영어) 인터페이스
