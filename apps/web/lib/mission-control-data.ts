export const departments = [
  {
    id: "agent:ceo_office",
    name: "CEO Office / Chief of Staff",
    role: "우선순위·결정·브리핑",
    mission: "대표의 의도를 오늘의 우선순위와 승인 요청으로 번역한다.",
    state: "active · strategy gated",
    metric: "decision_latency",
  },
  {
    id: "agent:cto",
    name: "Engineering / CTO",
    role: "제품·웹·자동화 개발",
    mission: "테스트와 증거가 있는 소프트웨어 변경을 출하한다.",
    state: "active · production gated",
    metric: "verified_shipments",
  },
  {
    id: "agent:design",
    name: "Design / Brand",
    role: "UI·브랜드·시각화",
    mission: "AI Native Company를 대표와 고객이 이해하는 화면으로 만든다.",
    state: "active · brand lock gated",
    metric: "approved_design_assets",
  },
  {
    id: "agent:growth",
    name: "Growth / Marketing",
    role: "콘텐츠·SEO·캠페인",
    mission: "콘텐츠와 캠페인 산출물을 만들고 발행 전 승인을 요청한다.",
    state: "active · publish gated",
    metric: "qualified_leads",
  },
  {
    id: "agent:cfo",
    name: "Finance / CFO",
    role: "현금·비용·송장",
    mission: "돈이 나가는 일과 비용 리스크를 보수적으로 검토한다.",
    state: "active · money gated",
    metric: "cash_visibility",
  },
  {
    id: "agent:general_counsel",
    name: "Legal / Compliance",
    role: "계약·NDA·컴플라이언스",
    mission: "법률/계약 리스크를 플래그하고 인간 검토로 넘긴다.",
    state: "active · legal advice blocked",
    metric: "risk_flags_caught",
  },
  {
    id: "agent:ops",
    name: "Ops / Automation",
    role: "문서·알림·반복 운영",
    mission: "Google Docs, 알림, cron, 워크플로우가 끊기지 않게 관리한다.",
    state: "active · prod gated",
    metric: "automation_reliability",
  },
] as const;

export const operatingFlow = [
  { id: "01", title: "대표 요청", text: "Telegram·웹 입력·회의 메모가 회사 업무로 들어온다." },
  { id: "02", title: "CEO Office 분류", text: "업무 성격과 위험도를 판단해 부서를 배정한다." },
  { id: "03", title: "부서 실행", text: "Growth·Engineering·Ops 등 AI 부서가 산출물을 만든다." },
  { id: "04", title: "승인 게이트", text: "돈·고객·법률·공개 발행은 대표 승인함으로 올라온다." },
  { id: "05", title: "증거 기록", text: "파일·테스트·URL·감사 로그가 Evidence Trail에 남는다." },
] as const;

export const approvalExamples = [
  { title: "LinkedIn 게시 승인", department: "Growth", risk: "노랑", action: "초안 확인 후 승인/수정" },
  { title: "광고비 50만원 초과", department: "Growth → CFO", risk: "빨강", action: "예산 승인 또는 보류" },
  { title: "내부 블로그 초안", department: "Growth", risk: "초록", action: "자동 생성 후 검토" },
] as const;

export const evidence = [
  "Google Docs / 로컬 Markdown 산출물",
  "pytest / npm verify / 브라우저 스크린샷",
  "GitHub PR / Vercel URL / public 200 OK",
  "SQLite rows: agents · actions · workflows · workflow_steps",
  "Audit trail: workflow_step_run · approval decision",
] as const;
