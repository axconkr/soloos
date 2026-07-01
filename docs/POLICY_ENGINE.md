# SoloOS — Policy Engine (v0.1)

**Purpose:** 에이전트가 요청한 액션을 실행할지, 결재로 올릴지, 거부할지 결정하는 규칙 엔진.

**Principle:** *"Autonomy by default in low-risk; approval by default when money, external voice, or irreversibility is involved."*

---

## 1. Decision Verdicts

| Verdict | 의미 | 다음 단계 |
|---------|------|-----------|
| `auto` | 규정상 자동 실행 허용 | Executor 즉시 실행 |
| `approval` | CEO 결재 필요 | Approval Queue enqueue |
| `deny` | 금지 (정책 위반) | Fail with reason, audit |
| `escalate` | 다른 에이전트에게 위임 | Router에 재라우팅 |

---

## 2. Rule Evaluation

**Order:** rules.yaml top-to-bottom, first match wins.  
**Language:** minimal CEL-like expression (parsed with `simpleeval`).

```yaml
# policy/rules.yaml
version: 1
default_verdict: approval    # unknown → 결재 요청 (안전)

rules:
  # ─── DENY (immutable no-go) ──────────────────────────
  - id: no_public_secrets
    when: "action.contains_secret == true"
    verdict: deny
    reason: "Secrets never leave the vault"

  - id: no_prod_delete
    when: "action.type == 'delete' and target.env == 'production'"
    verdict: deny

  # ─── ESCALATE ────────────────────────────────────────
  - id: cmo_overbudget
    when: "actor == 'agent:cmo' and action.type == 'spend_money' and params.amount_krw > 500000"
    verdict: escalate
    to: agent:finance
    reason: "Marketing spend over 500k → Finance review first"

  # ─── APPROVAL (default for risk classes) ─────────────
  - id: money_out
    when: "action.type in ['payment','subscription','ads_spend','refund']"
    verdict: approval
    risk: HIGH
    template: money_out.md.j2

  - id: external_message
    when: "action.type == 'send_email' and audience == 'external'"
    verdict: approval
    exempt_if: "template.id in ['auto_receipt','followup_v1','onboarding_step1']"
    risk: MED

  - id: content_publish
    when: "action.type == 'publish' and channel in ['blog','x','linkedin','youtube']"
    verdict: approval
    risk: MED
    template: content_publish.md.j2

  - id: contract_send
    when: "action.type == 'send_contract'"
    verdict: approval
    risk: HIGH

  - id: hire_or_fire
    when: "action.type in ['hire_vendor','fire_vendor','change_contractor']"
    verdict: approval
    risk: HIGH

  # ─── AUTO (safe internal ops) ────────────────────────
  - id: internal_drafts
    when: "action.type in ['draft_content','summarize','translate','extract']"
    verdict: auto
    risk: LOW

  - id: internal_ops
    when: "action.type in ['task_create','reminder','note_update','tag_lead','update_crm']"
    verdict: auto
    risk: LOW

  - id: read_only
    when: "action.type in ['search','recall','fetch','list','report']"
    verdict: auto
    risk: LOW

  - id: internal_notify
    when: "action.type == 'send_message' and audience == 'ceo'"
    verdict: auto
    risk: LOW
```

---

## 3. Evaluation Context

```python
context = {
    "actor": "agent:cmo",
    "action": {
        "type": "publish",
        "target_ref": "blog:ai-native-ops-3",
        "contains_secret": False,
    },
    "params": {...},
    "target": {"env": "production"},
    "channel": "blog",
    "audience": "external",
    "template": {"id": None},
}
```

Missing keys default to `None` — expressions use safe comparison.

---

## 4. Approval Templates

Each `verdict: approval` rule can reference a Jinja template that renders the Telegram card.

### 4.1 `money_out.md.j2`
```
💸 결재 요청 #{{ approval.id }}
━━━━━━━━━━━━━━━━━━━━━━━━━
에이전트: {{ actor }}
액션: {{ action.type }}
금액: ₩{{ '{:,}'.format(params.amount_krw) }}
용도: {{ params.purpose }}
공급자: {{ params.vendor }}
{% if params.recurring %}갱신 주기: {{ params.recurring }}{% endif %}

리스크: {{ risk }}
정책 규칙: {{ policy_rule }}
감사: #A-{{ audit_id }}
```

### 4.2 `content_publish.md.j2`
```
📝 발행 결재 #{{ approval.id }}
━━━━━━━━━━━━━━━━━━━━━━━━━
채널: {{ channel }}
제목: {{ params.title }}
분량: {{ params.word_count }}자

📎 초안: {{ params.preview_url }}
🔎 톤 검증: {{ params.tone_check }}
🔗 감사: #A-{{ audit_id }}
```

---

## 5. Guardrails (Hard-coded)

Bypass rules는 정책이 아니라 코드에 박아둔다. YAML로 무력화 불가능.

1. **Two-key rule for >₩5M**: 자동 승인 규칙이 있더라도 500만원 초과는 CEO 결재 강제
2. **PII redaction**: 외부 메시지 발송 전 이메일/전화/주민번호 패턴 자동 마스킹
3. **Rate limit**: 동일 액션 타입 60초 내 3회 초과 → 자동 정지 + 알림
4. **Reversibility check**: `delete/publish/send_email/payment`은 사전 스냅샷 필수, 스냅샷 실패 시 abort
5. **Human-only actions**: `legal_signoff`, `tax_filing`, `personnel_decision`는 절대 자동 실행 금지

---

## 6. Runtime Overrides

CEO는 텔레그램에서 즉시 정책 변경 가능:

| 명령 | 효과 |
|------|------|
| `/policy pause <rule_id>` | 규칙 일시 정지 (24h) |
| `/policy set <rule_id> risk=<LOW\|MED\|HIGH>` | 리스크 등급 조정 |
| `/policy trust <template_id> for <agent>` | 특정 템플릿 자동 승인 등록 |
| `/policy show` | 현 규칙 목록 + 최근 변경 |

모든 오버라이드는 감사 로그 + 24h 후 원복 알림.

---

## 7. Metrics

- `approval_rate = approved / (approved + rejected)`
- `median_approval_latency_sec`
- `auto_action_ratio = auto / total`  (Week 6 목표: ≥ 40%)
- `policy_violation_denied_count`

Dashboards: Ledger & Metrics (M6) 통합.

---

## 8. Change Management

- `policy/rules.yaml` 변경 시 PR 리뷰 (CODEOWNERS: `@phillip`)
- 신규 rule 추가 → shadow mode 48h (판정만 로그, 실제 적용 안 함) → CEO 승인 후 활성화
- 롤백: git revert + `soloos policy reload`
