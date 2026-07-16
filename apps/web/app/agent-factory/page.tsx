"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

type RuntimeRow = Record<string, string | number | boolean | null | object | unknown[]>;

type Snapshot = {
  counts?: Record<string, number>;
  agent_templates?: RuntimeRow[];
  agent_instances?: RuntimeRow[];
  approvals?: RuntimeRow[];
};

type FactoryResult = {
  status?: string;
  instance_id?: string;
  agent_id?: string;
  approval_id?: string;
  policy_status?: string;
  error?: string;
};

function text(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function statusText(value: unknown) {
  const raw = text(value, "draft");
  if (raw === "active") return "활성 투입";
  if (raw === "review" || raw === "approval_required") return "대표 승인 대기";
  return "초안 격리";
}

const blueprintCards = [
  {
    step: "01",
    title: "AgentSpec 설계",
    body: "직원이 역할, 미션, 권한, 도구/스킬, 메모리 범위, KPI, 예산·위험 등급을 먼저 적습니다.",
  },
  {
    step: "02",
    title: "Template 조립",
    body: "부서별 반복 업무를 AgentTemplate으로 묶어 재사용합니다. 화면 목적은 현황판이 아니라 제작 워크벤치입니다.",
  },
  {
    step: "03",
    title: "격리 실행",
    body: "생성된 agent instance는 draft/review 상태로 격리되고, active roster에는 바로 들어가지 않습니다.",
  },
];

const initialForm = {
  role_name: "고객 문의 1차 분류 에이전트",
  department: "agent:growth",
  slug: "customer-inquiry-triage",
  mission: "신규 고객 문의를 의도/긴급도/다음 액션 기준으로 분류하고 담당 부서에 전달합니다.",
  skills: "inbox_triage, korean_response_draft",
  authority: "고객에게 직접 발송 금지, 개인정보 저장 금지, CEO 승인 전 프로덕션 자동화 금지",
  kpi: "first_response_time, routing_accuracy",
  risk_tier: "MED",
  created_by: "employee:web",
};

export default function AgentFactoryPage() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [snapshotState, setSnapshotState] = useState("snapshot loading");
  const [form, setForm] = useState(initialForm);
  const [factoryResult, setFactoryResult] = useState<FactoryResult | null>(null);
  const [factoryBusy, setFactoryBusy] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/soloos-snapshot.json", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`snapshot ${res.status}`))))
      .then((data: Snapshot) => {
        if (!active) return;
        setSnapshot(data);
        setSnapshotState("snapshot connected");
      })
      .catch(() => {
        if (!active) return;
        setSnapshotState("snapshot unavailable · using empty factory view");
      });
    return () => {
      active = false;
    };
  }, []);

  const templates = useMemo(() => snapshot?.agent_templates ?? [], [snapshot]);
  const instances = useMemo(() => snapshot?.agent_instances ?? [], [snapshot]);
  const approvals = useMemo(() => snapshot?.approvals ?? [], [snapshot]);
  const pendingInstances = instances.filter((instance) => text(instance.policy_status).includes("approval"));
  const latestInstance = instances[0];
  const currentInstanceId = factoryResult?.instance_id || text(latestInstance?.id, "");

  async function submitFactory(mode: "create_draft" | "request_approval", event?: FormEvent) {
    event?.preventDefault();
    setFactoryBusy(true);
    setFactoryResult(null);
    try {
      const payload = mode === "create_draft"
        ? { mode, ...form }
        : { mode, instance_id: currentInstanceId, requested_by: form.created_by };
      const response = await fetch("/api/agent-factory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      setFactoryResult(data);
      if (data.instance_id) {
        setSnapshot((prev) => ({
          ...(prev ?? {}),
          agent_instances: [
            {
              id: data.instance_id,
              agent_id: data.agent_id,
              slug: form.slug,
              mission: form.mission,
              lifecycle_status: data.lifecycle_status || "draft",
              policy_status: data.policy_status || "review_required",
            },
            ...((prev?.agent_instances ?? []).filter((row) => row.id !== data.instance_id)),
          ],
        }));
      }
    } catch (error) {
      setFactoryResult({ status: "agent_factory_failed", error: error instanceof Error ? error.message : "unknown_error" });
    } finally {
      setFactoryBusy(false);
    }
  }

  return (
    <main className="factory-shell">
      <header className="factory-hero">
        <nav className="factory-nav" aria-label="Agent Factory navigation">
          <Link href="/">← Mission Control로 돌아가기</Link>
          <span>TODO: brand asset required · Phillip/AX Consulting 공식 로고 필요</span>
        </nav>
        <p className="factory-kicker">Employee Workbench · governed agent creation layer</p>
        <h1>AX Agent Factory</h1>
        <p className="factory-subtitle">
          이 화면은 Mission Control이 아닙니다. 대표용 현황판이 아니라 AI 직원과 부서가 필요한 에이전트를 만들고,
          권한을 제한한 뒤 대표 승인 전까지 격리하는 제작 라인입니다.
        </p>
      </header>

      <section className="factory-command-strip" aria-label="Factory status">
        <div><span>Templates</span><strong>{Number(snapshot?.counts?.agent_templates ?? templates.length)}</strong></div>
        <div><span>Instances</span><strong>{Number(snapshot?.counts?.agent_instances ?? instances.length)}</strong></div>
        <div><span>Approval Gate</span><strong>{pendingInstances.length}</strong></div>
        <div><span>Snapshot</span><strong>{snapshotState}</strong></div>
      </section>

      <section className="employee-builder" aria-label="직원이 에이전트 만들기">
        <div>
          <p className="factory-kicker">직원이 에이전트 만들기</p>
          <h2>AgentSpec을 작성하고 draft instance를 생성합니다.</h2>
          <p>아래 폼은 단순 대시보드가 아니라 `/api/agent-factory`를 호출해 실제 SoloOS Agent Factory CLI에 draft를 만들고, 이어서 대표 승인 요청까지 연결합니다.</p>
        </div>
        <form className="agent-builder-form" onSubmit={(event) => submitFactory("create_draft", event)}>
          <label>역할 / 이름<input value={form.role_name} onChange={(event) => setForm({ ...form, role_name: event.target.value })} /></label>
          <label>담당 부서
            <select value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })}>
              <option value="agent:growth">Growth</option>
              <option value="agent:cto">CTO</option>
              <option value="agent:design">Design</option>
              <option value="agent:ops">Ops</option>
              <option value="agent:cfo">CFO</option>
              <option value="agent:general_counsel">Legal</option>
              <option value="agent:ceo_office">CEO Office</option>
            </select>
          </label>
          <label>Slug<input value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} /></label>
          <label className="wide">미션<textarea value={form.mission} onChange={(event) => setForm({ ...form, mission: event.target.value })} /></label>
          <label className="wide">권한 제한<textarea value={form.authority} onChange={(event) => setForm({ ...form, authority: event.target.value })} /></label>
          <label>도구/스킬<input value={form.skills} onChange={(event) => setForm({ ...form, skills: event.target.value })} /></label>
          <label>KPI<input value={form.kpi} onChange={(event) => setForm({ ...form, kpi: event.target.value })} /></label>
          <label>Risk
            <select value={form.risk_tier} onChange={(event) => setForm({ ...form, risk_tier: event.target.value })}>
              <option value="LOW">LOW</option>
              <option value="MED">MED</option>
              <option value="HIGH">HIGH</option>
            </select>
          </label>
          <div className="factory-actions wide">
            <button type="submit" disabled={factoryBusy}>{factoryBusy ? "생성 중…" : "Agent draft 생성"}</button>
            <button type="button" disabled={factoryBusy || !currentInstanceId} onClick={() => submitFactory("request_approval")}>대표 승인 요청</button>
          </div>
        </form>
        <aside className="factory-result" aria-live="polite">
          <span>Factory API result</span>
          <strong>{factoryResult?.status ?? "대기 중"}</strong>
          <p>instance_id: {(factoryResult?.instance_id ?? currentInstanceId) || "-"}</p>
          <p>approval_id: {factoryResult?.approval_id ?? "-"}</p>
          <p>policy: {factoryResult?.policy_status ?? "draft → review_required → approval_required"}</p>
          {factoryResult?.error ? <p>error: {factoryResult.error}</p> : null}
        </aside>
      </section>

      <section className="factory-lanes" aria-label="Agent creation lanes">
        <article className="factory-lane build-lane">
          <p>Build Lane</p>
          <h2>직원이 필요한 AgentSpec을 설계합니다.</h2>
          <div className="factory-blueprint-list">
            {blueprintCards.map((card) => (
              <div key={card.step}>
                <span>{card.step}</span>
                <strong>{card.title}</strong>
                <p>{card.body}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="factory-lane governance-lane">
          <p>Governance Gate</p>
          <h2>권한·KPI·위험도를 붙이고 승인 전까지 잠급니다.</h2>
          <div className="factory-spec-card">
            <span>Current template</span>
            <strong>{templates[0] ? text(templates[0].name) : "부서별 AgentTemplate 대기"}</strong>
            <p>{templates[0] ? text(templates[0].mission_template) : "공식 템플릿이 없으면 직원은 새 AgentSpec을 만들 수 있지만, CEO 승인 전까지 active roster에 들어가지 않습니다."}</p>
          </div>
          <div className="factory-spec-card warning">
            <span>Brand / production lock</span>
            <strong>CEO 승인 전 외부 접촉·프로덕션·브랜드 권한 없음</strong>
            <p>OpenManus UX 패턴은 참고만 하고, SoloOS 고유 lifecycle과 evidence gate로 운영합니다.</p>
          </div>
        </article>

        <article className="factory-lane launch-lane">
          <p>Launch Rail</p>
          <h2>승인된 인스턴스만 실행 레이어로 이동합니다.</h2>
          <div className="launch-card">
            <span>Latest instance</span>
            <strong>{latestInstance ? text(latestInstance.slug) : "생성된 agent instance 없음"}</strong>
            <p>{latestInstance ? text(latestInstance.mission) : "현재 factory queue는 비어 있습니다. 직원 요청이 들어오면 draft → review → approval_required → active 순서로 이동합니다."}</p>
          </div>
          <div className="launch-card">
            <span>Lifecycle state</span>
            <strong>{latestInstance ? statusText(latestInstance.lifecycle_status ?? latestInstance.policy_status) : "초안 대기"}</strong>
            <p>활성화는 `soloos agent-factory activate`와 승인 ID가 있을 때만 가능합니다.</p>
          </div>
          <div className="launch-card muted">
            <span>Approval rows</span>
            <strong>{approvals.length}</strong>
            <p>승인 기록은 Mission Control 승인함과 audit trail에 연결됩니다.</p>
          </div>
        </article>
      </section>
    </main>
  );
}
