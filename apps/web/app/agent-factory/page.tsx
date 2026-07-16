"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type RuntimeRow = Record<string, string | number | boolean | null | object | unknown[]>;

type Snapshot = {
  counts?: Record<string, number>;
  agent_templates?: RuntimeRow[];
  agent_instances?: RuntimeRow[];
  approvals?: RuntimeRow[];
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

export default function AgentFactoryPage() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [snapshotState, setSnapshotState] = useState("snapshot loading");

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
