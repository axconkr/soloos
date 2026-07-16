"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { approvalExamples, departments, evidence, operatingFlow } from "../lib/mission-control-data";

type RuntimeRow = Record<string, string | number | boolean | null | object | unknown[]>;

type Snapshot = {
  generated_at?: number;
  counts?: Record<string, number>;
  agents?: RuntimeRow[];
  agent_templates?: RuntimeRow[];
  agent_instances?: RuntimeRow[];
  actions?: RuntimeRow[];
  workflows?: RuntimeRow[];
  workflow_steps?: RuntimeRow[];
  approvals?: RuntimeRow[];
  audit_events?: RuntimeRow[];
};

const fallbackAgents = departments.map((department) => ({
  id: department.id,
  name: department.name,
  mission: department.mission,
  status: "active",
  skills: [department.role],
  kpi: { primary: department.metric },
}));

function text(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function formatTime(epoch?: unknown) {
  if (typeof epoch !== "number") return "아직 없음";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(epoch * 1000));
}

function departmentLabel(actor: unknown) {
  const value = text(actor, "AI 부서");
  const normalized = value.startsWith("agent:") ? value : `agent:${value}`;
  const legacyMap: Record<string, string> = {
    "agent:cmo": "Growth / Marketing",
    "agent:sales": "Growth / Marketing",
    "agent:finance": "Finance / CFO",
  };
  if (legacyMap[normalized]) return legacyMap[normalized];
  const known = departments.find((department) => department.id === normalized || department.id === value || department.name === value);
  return known?.name ?? value;
}

function normalizeAgentName(agent: RuntimeRow) {
  const id = text(agent.id, "");
  const known = departments.find((department) => department.id === id || department.name === agent.name);
  return known?.name ?? text(agent.name, "AI 부서");
}

function agentMission(agent: RuntimeRow) {
  const id = text(agent.id, "");
  const name = text(agent.name).toLowerCase();
  const known = departments.find((department) => department.id === id || department.name === agent.name);
  if (known) return known.mission;
  if (name.includes("growth") || name.includes("cmo")) return "콘텐츠·캠페인 실행";
  if (name.includes("engineering") || name.includes("cto")) return "제품과 자동화 개발";
  if (name.includes("design")) return "브랜드와 UI 시각화";
  if (name.includes("finance") || name.includes("cfo")) return "비용·현금 확인";
  if (name.includes("legal")) return "계약·컴플라이언스 리스크 확인";
  if (name.includes("ops")) return "운영 자동화";
  return text(agent.mission, "회사 운영 지원");
}

function statusTone(status?: unknown) {
  const value = text(status, "").toLowerCase();
  if (value.includes("failed") || value.includes("error")) return "danger";
  if (value.includes("pending") || value.includes("running")) return "warn";
  return "good";
}

function healthScore(snapshot: Snapshot | null, agents: RuntimeRow[]) {
  const counts = snapshot?.counts ?? {};
  const totalActions = Number(counts.actions ?? 0);
  const totalWorkflows = Number(counts.workflows ?? 0);
  const auditEvents = Number(counts.audit_events ?? 0);
  const failedSteps = snapshot?.workflow_steps?.filter((step) => text(step.status).includes("failed")).length ?? 0;
  const activeAgentBonus = Math.min(28, agents.length * 4);
  const executionBonus = Math.min(24, (totalActions + totalWorkflows) * 6);
  const evidenceBonus = Math.min(22, auditEvents * 2);
  const penalty = failedSteps * 15;
  return Math.max(42, Math.min(96, 34 + activeAgentBonus + executionBonus + evidenceBonus - penalty));
}

function riskLabel(snapshot: Snapshot | null) {
  const pending = snapshot?.actions?.filter((action) => text(action.status) === "pending").length ?? 0;
  const failed = snapshot?.workflow_steps?.filter((step) => text(step.status) === "failed").length ?? 0;
  if (failed > 0) return { label: "빨강", detail: "실패한 작업이 있어 즉시 확인 필요", tone: "danger" };
  if (pending > 0) return { label: "노랑", detail: "대표 승인 또는 다음 실행 대기 중", tone: "warn" };
  return { label: "초록", detail: "내부 실행과 기록은 정상 범위", tone: "good" };
}

type ApprovalItem = {
  approval_id?: string;
  title: string;
  department: string;
  risk: string;
  action: string;
};

function approvalRisk(risk: unknown) {
  const value = text(risk, "LOW").toUpperCase();
  if (value.includes("HIGH") || value.includes("CRITICAL")) return "빨강";
  if (value.includes("MED") || value.includes("WARN")) return "노랑";
  return "초록";
}

function approvalKey(item: ApprovalItem, index: number) {
  return item.approval_id || `${item.title}-${item.department}-${index}`;
}

function approvalItems(snapshot: Snapshot | null): ApprovalItem[] {
  const pendingApprovals = snapshot?.approvals?.filter((approval) => text(approval.status) === "pending") ?? [];
  if (pendingApprovals.length) {
    return pendingApprovals.slice(0, 3).map((approval) => ({
      approval_id: text(approval.id),
      title: text(approval.action_type, "승인 대기 작업"),
      department: departmentLabel(approval.agent_id),
      risk: approvalRisk(approval.risk),
      action: `${text(approval.target, "대상 미지정")} · 대표가 승인/거절/수정 요청 결정`,
    }));
  }
  const latestStep = snapshot?.workflow_steps?.[0];
  const pendingActions = snapshot?.actions?.filter((action) => text(action.status) === "pending") ?? [];
  if (pendingActions.length) {
    return pendingActions.slice(0, 3).map((action) => ({
      approval_id: undefined,
      title: text(action.action_type, "승인 대기 작업"),
      department: departmentLabel(action.actor),
      risk: "노랑",
      action: "대표가 승인/거절/수정 요청 결정",
    }));
  }
  if (latestStep?.status === "success") {
    return [
      {
        approval_id: undefined,
        title: "완료 산출물 검토",
        department: departmentLabel(latestStep.actor),
        risk: "노랑",
        action: "초안 확인 후 공개 발행 여부 결정",
      },
      ...approvalExamples.slice(1).map((item) => ({ ...item, approval_id: undefined })),
    ];
  }
  return approvalExamples.map((item) => ({ ...item, approval_id: undefined }));
}

export default function Home() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [snapshotState, setSnapshotState] = useState("연결 중");
  const [companyCommand, setCompanyCommand] = useState("이번 주 SoloOS 콘텐츠 3개 만들어줘");
  const [commandFeedback, setCommandFeedback] = useState("대표 요청 대기 중");
  const [approvalFeedback, setApprovalFeedback] = useState("아직 처리한 승인 없음");
  const [selectedDepartmentId, setSelectedDepartmentId] = useState<string>(departments[0].id);

  useEffect(() => {
    let alive = true;
    async function loadSnapshot() {
      try {
        const response = await fetch(`/soloos-snapshot.json?ts=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`snapshot ${response.status}`);
        const json = (await response.json()) as Snapshot;
        if (alive) {
          setSnapshot(json);
          setSnapshotState("실시간 연결됨");
        }
      } catch (_error) {
        if (alive) setSnapshotState("스냅샷 확인 필요");
      }
    }
    loadSnapshot();
    const timer = window.setInterval(loadSnapshot, 5000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const counts = snapshot?.counts ?? {};
  const agents = snapshot?.agents?.length ? snapshot.agents : fallbackAgents;
  const templates = snapshot?.agent_templates ?? [];
  const factoryInstances = snapshot?.agent_instances ?? [];
  const pendingFactoryInstances = factoryInstances.filter((instance) => text(instance.policy_status) === "approval_required" || text(instance.lifecycle_status) === "review");
  const latestFactoryInstance = factoryInstances[0];
  const selectedAgent = agents.find((agent) => text(agent.id) === selectedDepartmentId) ?? agents[0];
  const approvals = approvalItems(snapshot);
  const latestWorkflow = snapshot?.workflows?.[0];
  const latestStep = snapshot?.workflow_steps?.[0];
  const latestAction = snapshot?.actions?.[0];
  const latestAudit = snapshot?.audit_events?.[0];
  const completedWork = snapshot?.workflow_steps?.filter((step) => text(step.status) === "success").length ?? 0;
  const activeAgents = Number(counts.agents ?? agents.length);
  const auditEvents = Number(counts.audit_events ?? 0);
  const score = healthScore(snapshot, agents);
  const risk = riskLabel(snapshot);
  const companyStatus = risk.tone === "danger" ? "주의 필요" : risk.tone === "warn" ? "대표 확인 필요" : "정상 운영";
  const plainSummary = latestStep?.status === "success"
    ? "AI 부서가 대표 요청을 업무로 바꾸고, 산출물·검증·감사 기록까지 남겼습니다."
    : "AI Native Company는 대기 중입니다. 대표가 요청을 넣으면 부서 배정부터 증거 기록까지 진행됩니다.";
  const nextAction = latestStep?.output_ref
    ? "완료 산출물 확인 → 공개 발행/고객 전달 여부 승인"
    : "Ask the Company에 첫 업무를 입력해 가상회사 운영 흐름을 생성";

  const scoreCards = useMemo(() => [
    { label: "회사 건강도", value: `${score}/100`, hint: "부서 준비도·실행·증거 로그를 합친 대표용 신호" },
    { label: "AI 부서", value: `${activeAgents}개`, hint: "대표 대신 움직이는 가상회사 조직도" },
    { label: "끝난 일", value: `${completedWork}건`, hint: "완료된 workflow step" },
    { label: "증거 로그", value: `${auditEvents}개`, hint: "나중에 추적 가능한 기록" },
  ], [activeAgents, auditEvents, completedWork, score]);

  async function submitCompanyCommand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const command = companyCommand.trim();
    if (!command) {
      setCommandFeedback("요청 내용을 먼저 입력해주세요");
      return;
    }
    setCommandFeedback("CEO Office가 요청을 접수하는 중...");
    try {
      const response = await fetch("/api/company-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, source: "mission_control_web" }),
      });
      if (!response.ok) throw new Error(`command ${response.status}`);
      const result = await response.json();
      setCommandFeedback(`요청이 CEO Office로 접수되었습니다 · ${departmentLabel(result.suggested_department)}`);
    } catch (_error) {
      setCommandFeedback("요청 접수 실패 · CLI/Telegram으로 다시 보내주세요");
    }
  }

  async function sendApprovalDecision(item: ReturnType<typeof approvalItems>[number], decision: "approve" | "reject" | "revise") {
    const label = decision === "approve" ? "승인" : decision === "reject" ? "반려" : "수정요청";
    setApprovalFeedback(`${item.title} · ${label} 기록 중...`);
    try {
      const response = await fetch("/api/approval-decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: item.title, department: item.department, approval_id: item.approval_id, decision }),
      });
      if (!response.ok) throw new Error(`approval ${response.status}`);
      setApprovalFeedback(`${item.title} · ${label} 결정이 Evidence Trail에 기록되었습니다`);
    } catch (_error) {
      setApprovalFeedback(`${item.title} · ${label} 기록 실패`);
    }
  }

  return (
    <main className="ceo-shell">
      <header className="ceo-hero">
        <div className="brand-bar" aria-label="AX Consulting brand status">
          <p className="eyebrow">CEO Cockpit · powered by SoloOS</p>
          <div className="brand-blocker" role="status">TODO: brand asset required · Phillip/AX Consulting 공식 로고 필요</div>
        </div>
        <div className="hero-row">
          <section>
            <h1>AX Consulting Mission Control</h1>
            <p className="subtitle">
              한국어-first AI 회사 운영 UI입니다. 대표가 AI Native Company를 가장 쉽게 이해하는 화면으로,
              복잡한 agent 로그가 아니라
              <strong> 가상회사가 잘 운영되는지</strong>, 어디가 막혔는지, 무엇을 승인해야 하는지만 보여줍니다.
            </p>
          </section>
          <aside className={`status-card ${risk.tone}`}>
            <span>현재 상태</span>
            <strong>{companyStatus}</strong>
            <p>{snapshotState} · {formatTime(snapshot?.generated_at)}</p>
          </aside>
        </div>
      </header>

      <section className="answer-card">
        <div>
          <p className="section-label">한 줄 결론</p>
          <h2>{plainSummary}</h2>
        </div>
        <div className={`traffic-light ${risk.tone}`} aria-label={`위험도 ${risk.label}`}>
          <span className="light" />
          <strong>{risk.label}</strong>
          <small>초록 / 노랑 / 빨강</small>
        </div>
      </section>

      <section className="score-grid" aria-label="쉬운 회사 운영 숫자">
        {scoreCards.map((card) => (
          <article className="score-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.hint}</p>
          </article>
        ))}
      </section>

      <section className="ceo-grid top-grid">
        <article className="panel panel-focus daily-brief">
          <p className="section-label">Daily CEO Brief</p>
          <h2>오늘 회사가 어떻게 돌아가고 있나요?</h2>
          <div className="brief-stack">
            <div><span>완료</span><strong>{completedWork ? `${completedWork}건 완료` : "아직 완료 작업 없음"}</strong></div>
            <div><span>막힘</span><strong>{risk.tone === "danger" ? "실패 작업 확인 필요" : "치명적 막힘 없음"}</strong></div>
            <div><span>다음 액션</span><strong>{nextAction}</strong></div>
          </div>
        </article>

        <article className="panel approval-inbox">
          <p className="section-label">Approval Inbox</p>
          <h2>대표 승인함</h2>
          <div className="approval-list">
            {approvals.map((item, index) => (
              <div className="approval-item" key={approvalKey(item, index)}>
                <span className={`risk-pill ${item.risk === "빨강" ? "danger" : item.risk === "노랑" ? "warn" : "good"}`}>{item.risk}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.department} · {item.action}</p>
                  <div className="approval-actions" aria-label={`${item.title} 결정`}>
                    <button type="button" onClick={() => sendApprovalDecision(item, "approve")}>승인</button>
                    <button type="button" onClick={() => sendApprovalDecision(item, "reject")}>반려</button>
                    <button type="button" onClick={() => sendApprovalDecision(item, "revise")}>수정요청</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p className="feedback-line">{approvalFeedback}</p>
        </article>
      </section>

      <section className="panel company-map">
        <div className="section-head">
          <div>
            <p className="section-label">운영 흐름 지도</p>
            <h2>대표 요청이 회사 실행으로 바뀌는 과정</h2>
          </div>
          <span className="map-badge">Ask the Company → 승인 → Evidence Trail</span>
        </div>
        <div className="flow-line">
          {operatingFlow.map((step) => (
            <article className="flow-step" key={step.id}>
              <span>{step.id}</span>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel ask-card">
        <div>
          <p className="section-label">Ask the Company</p>
          <h2>대표는 명령어를 외우지 않고 회사에 말하듯 요청합니다.</h2>
          <p>요청은 먼저 CEO Office로 접수되고, 성격에 맞는 부서로 라우팅될 준비 상태로 기록됩니다.</p>
        </div>
        <form className="ask-form" onSubmit={submitCompanyCommand}>
          <label htmlFor="company-command">회사에 요청 입력</label>
          <textarea
            id="company-command"
            value={companyCommand}
            onChange={(event) => setCompanyCommand(event.target.value)}
            rows={4}
          />
          <button type="submit">회사에 요청 보내기</button>
          <p className="feedback-line">{commandFeedback}</p>
          <div className="prompt-examples" aria-label="요청 예시">
            <button type="button" onClick={() => setCompanyCommand("이번 주 SoloOS 콘텐츠 3개 만들어줘")}>이번 주 SoloOS 콘텐츠 3개 만들어줘</button>
            <button type="button" onClick={() => setCompanyCommand("신규 문의 답장 초안 작성해줘")}>신규 문의 답장 초안 작성해줘</button>
            <button type="button" onClick={() => setCompanyCommand("웹사이트 상태 확인하고 문제 있으면 고쳐줘")}>웹사이트 상태 확인하고 문제 있으면 고쳐줘</button>
          </div>
        </form>
      </section>

      <section className="panel department-board">
        <div className="section-head">
          <div>
            <p className="section-label">7개 부서 운영 현황</p>
            <h2>AI 직원 현황</h2>
          </div>
          <span className="map-badge">조직도처럼 보이고, 워크플로우처럼 실행</span>
        </div>
        <div className="department-grid">
          {agents.map((agent) => (
            <article className={`department-card ${text(agent.id) === selectedDepartmentId ? "selected" : ""}`} key={text((agent as RuntimeRow).id ?? agent.name)}>
              <div className="department-top">
                <div className="avatar">{normalizeAgentName(agent).slice(0, 1)}</div>
                <span className={`status-dot ${statusTone(agent.status)}`}>{text(agent.status, "active")}</span>
              </div>
              <strong>{normalizeAgentName(agent)}</strong>
              <p>{agentMission(agent)}</p>
              <small>KPI: {text((agent.kpi as RuntimeRow | undefined)?.primary, "operational_health")}</small>
              <button type="button" className="detail-button" onClick={() => setSelectedDepartmentId(text(agent.id))}>부서 상세 열기</button>
            </article>
          ))}
        </div>
        <aside className="department-detail" aria-label="부서 상세 보기">
          <p className="section-label">부서 상세 보기</p>
          <h3>{normalizeAgentName(selectedAgent)}</h3>
          <p>{agentMission(selectedAgent)}</p>
          <div className="detail-metrics">
            <div><span>상태</span><strong>{text(selectedAgent.status, "active")}</strong></div>
            <div><span>대표가 보는 KPI</span><strong>{text((selectedAgent.kpi as RuntimeRow | undefined)?.primary, "operational_health")}</strong></div>
            <div><span>승인 원칙</span><strong>외부 발행·돈·법률·고객 접촉은 대표 승인</strong></div>
          </div>
        </aside>
      </section>

      <section className="panel agent-factory-board">
        <div className="section-head">
          <div>
            <p className="section-label">Agent Factory / Employee Workbench</p>
            <h2>직원이 필요한 에이전트를 만들고, 승인 후 회사 실행 레이어에 올립니다.</h2>
            <p>
              Mission Control은 결과를 보는 화면이고, 이 레이어는 직원이 업무별 AgentSpec을 만들고
              권한·KPI·위험도를 붙여 검토 요청하는 SoloOS의 밑바닥입니다.
            </p>
          </div>
          <a className="map-badge factory-route-link" href="/agent-factory">별도 Factory 화면 열기 → /agent-factory</a>
        </div>
        <div className="factory-grid">
          <article>
            <span>템플릿</span>
            <strong>{templates.length ? text(templates[0].name) : "부서별 AgentTemplate 준비"}</strong>
            <p>{templates.length ? text(templates[0].mission_template) : "역할·미션·기본 권한·KPI를 재사용 가능한 생성 규격으로 관리"}</p>
          </article>
          <article>
            <span>최근 생성 인스턴스</span>
            <strong>{latestFactoryInstance ? text(latestFactoryInstance.slug) : "아직 생성된 에이전트 없음"}</strong>
            <p>{latestFactoryInstance ? text(latestFactoryInstance.mission) : "직원이 필요한 순간 생성하고 roster 투입 전까지 draft/review 상태로 격리"}</p>
          </article>
          <article>
            <span>대표 승인 대기</span>
            <strong>{pendingFactoryInstances.length ? `${pendingFactoryInstances.length}건 approval_required` : "0건"}</strong>
            <p>외부 접촉·프로덕션·브랜드·비용 권한은 CEO 승인 전 active roster에 들어가지 않습니다.</p>
          </article>
        </div>
      </section>

      <section className="ceo-grid">
        <article className="panel evidence-panel">
          <p className="section-label">Evidence Trail</p>
          <h2>AI가 했다는 말보다 증거를 먼저 남깁니다.</h2>
          <ul>
            {evidence.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>

        <article className="panel panel-focus">
          <p className="section-label">방금 끝난 일</p>
          <h2>{text(latestStep?.output_text, "아직 완료된 작업이 없습니다")}</h2>
          <div className="plain-list">
            <div><span>작업</span><strong>{text(latestStep?.id, "대기 중")}</strong></div>
            <div><span>결과</span><strong>{text(latestStep?.status, "waiting")}</strong></div>
            <div><span>산출물</span><strong>{text(latestStep?.output_ref, "아직 없음")}</strong></div>
          </div>
        </article>
      </section>

      <details className="advanced-panel">
        <summary>상세 로그 보기</summary>
        <div className="advanced-grid">
          <div><span>Latest action</span><strong>{text(latestAction?.id)} · {text(latestAction?.status)}</strong><p>{text(latestAction?.action_type)} → {text(latestAction?.snapshot_ref)}</p></div>
          <div><span>Latest workflow</span><strong>{text(latestWorkflow?.id)} · {text(latestWorkflow?.status)}</strong><p>{text(latestWorkflow?.title, text(latestWorkflow?.workflow_type))}</p></div>
          <div><span>Latest audit</span><strong>{text(latestAudit?.id)} · {text(latestAudit?.status)}</strong><p>{text(latestAudit?.action_type)} · {text(latestAudit?.target)}</p></div>
        </div>
      </details>
    </main>
  );
}
