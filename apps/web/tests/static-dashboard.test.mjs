import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const requiredFiles = [
  'app/page.tsx',
  'app/globals.css',
  'app/api/company-command/route.ts',
  'app/api/approval-decision/route.ts',
  'lib/mission-control-data.ts',
  'lib/mission-control-client.ts',
  'lib/api-guard.ts',
  'middleware.ts',
  'package.json',
];

for (const file of requiredFiles) {
  const path = join(root, file);
  if (!existsSync(path)) {
    throw new Error(`Missing required dashboard file: ${file}`);
  }
}

const page = readFileSync(join(root, 'app/page.tsx'), 'utf8');
const layout = readFileSync(join(root, 'app/layout.tsx'), 'utf8');
const css = readFileSync(join(root, 'app/globals.css'), 'utf8');
const data = readFileSync(join(root, 'lib/mission-control-data.ts'), 'utf8');
const commandRoute = readFileSync(join(root, 'app/api/company-command/route.ts'), 'utf8');
const approvalRoute = readFileSync(join(root, 'app/api/approval-decision/route.ts'), 'utf8');
const missionClient = readFileSync(join(root, 'lib/mission-control-client.ts'), 'utf8');
const apiGuard = readFileSync(join(root, 'lib/api-guard.ts'), 'utf8');
const middleware = readFileSync(join(root, 'middleware.ts'), 'utf8');
const packageJson = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
const repoRoot = join(root, '..', '..');
const openManusAnalysisPath = join(repoRoot, 'docs/OPENMANUS_REFERENCE_ANALYSIS.md');
if (!existsSync(openManusAnalysisPath)) {
  throw new Error('Missing required OpenManus reference analysis doc');
}
const openManusAnalysis = readFileSync(openManusAnalysisPath, 'utf8');
const webDeployment = readFileSync(join(repoRoot, 'docs/WEB_DEPLOYMENT.md'), 'utf8');
const readme = readFileSync(join(repoRoot, 'README.md'), 'utf8');

const expectations = [
  ['page title', page, 'AX Consulting Mission Control'],
  ['SoloOS engine label', page, 'powered by SoloOS'],
  ['CEO cockpit section', page, 'CEO Cockpit'],
  ['plain Korean CEO summary', page, '오늘 회사가 어떻게 돌아가고 있나요?'],
  ['virtual company explanation', page, '가상회사가 잘 운영되는지'],
  ['AI native company phrase', page, 'AI Native Company'],
  ['company health score', page, '회사 건강도'],
  ['daily CEO brief', page, 'Daily CEO Brief'],
  ['approval inbox', page, 'Approval Inbox'],
  ['approval buttons approve', page, '승인'],
  ['approval buttons reject', page, '반려'],
  ['approval buttons revise', page, '수정요청'],
  ['approval API call', page, '/api/approval-decision'],
  ['department command center', page, '7개 부서 운영 현황'],
  ['department detail panel', page, '부서 상세 보기'],
  ['selected department state', page, 'selectedDepartmentId'],
  ['department button affordance', page, '부서 상세 열기'],
  ['visual operating map', page, '운영 흐름 지도'],
  ['plain-language risk light', page, '초록 / 노랑 / 빨강'],
  ['ask the company CTA', page, 'Ask the Company'],
  ['ask input textarea', page, '회사에 요청 입력'],
  ['ask submit button', page, '회사에 요청 보내기'],
  ['ask command API call', page, '/api/company-command'],
  ['ask queued feedback', page, '요청이 CEO Office로 접수되었습니다'],
  ['evidence trail', page, 'Evidence Trail'],
  ['live snapshot fetch', page, 'soloos-snapshot.json'],
  ['advanced details section', page, '상세 로그'],
  ['CEO Office fixture', data, 'CEO Office / Chief of Staff'],
  ['Engineering fixture', data, 'Engineering / CTO'],
  ['Design fixture', data, 'Design / Brand'],
  ['Growth fixture', data, 'Growth / Marketing'],
  ['Finance fixture', data, 'Finance / CFO'],
  ['Legal fixture', data, 'Legal / Compliance'],
  ['Ops fixture', data, 'Ops / Automation'],
  ['visual company CSS', css, 'company-map'],
  ['approval inbox CSS', css, 'approval-inbox'],
  ['ask form CSS', css, 'ask-form'],
  ['department detail CSS', css, 'department-detail'],
  ['approval id passed from UI', page, 'approval_id'],
  ['approval list uses stable unique key helper', page, 'approvalKey(item, index)'],
  ['command route recognizes inbound inquiries', commandRoute, '문의'],
  ['command route recognizes reply drafts', commandRoute, '답장'],
  ['command route uses mission client', commandRoute, 'askMissionControl'],
  ['command route authorizes API', commandRoute, 'authorizeWebApi'],
  ['command route uses bounded JSON parser', commandRoute, 'readBoundedJson'],
  ['command route status', missionClient, 'routed_to_soloos'],
  ['approval route accepts approval id', approvalRoute, 'approval_id'],
  ['approval route uses mission client', approvalRoute, 'decideMissionControl'],
  ['approval route requires approval id', approvalRoute, 'approval_id_required'],
  ['approval route authorizes API', approvalRoute, 'authorizeWebApi'],
  ['approval route uses bounded JSON parser', approvalRoute, 'readBoundedJson'],
  ['approval route writes real decision status', missionClient, 'recorded_in_soloos'],
  ['approval route decisions', missionClient, 'approve'],
  ['mission client keeps fallback command JSONL', missionClient, 'web-commands.jsonl'],
  ['mission client keeps fallback approval JSONL', missionClient, 'web-approvals.jsonl'],
  ['mission client invokes child process locally', missionClient, 'execFile'],
  ['mission client calls SoloOS Mission Control', missionClient, 'mission-control'],
  ['mission client asks real SoloOS queue', missionClient, 'ask'],
  ['mission client decides real approvals', missionClient, 'decide'],
  ['mission client supports remote deployment URL', missionClient, 'SOLOOS_MISSION_CONTROL_URL'],
  ['mission client remote timeout', missionClient, 'AbortSignal.timeout'],
  ['mission client remote token requires HTTPS', missionClient, 'must use https'],
  ['mission client disables local uv on Vercel', missionClient, 'local uv execution is disabled in serverless'],
  ['api guard supports inbound web token', apiGuard, 'SOLOOS_WEB_API_TOKEN'],
  ['api guard supports Basic auth', apiGuard, 'SOLOOS_WEB_BASIC_PASSWORD'],
  ['api guard bounds input', apiGuard, 'boundedString'],
  ['api guard has request size guard', apiGuard, 'request_too_large'],
  ['api guard redacts errors', apiGuard, 'stableError'],
  ['middleware protects hosted dashboard', middleware, 'Authentication required'],
  ['middleware covers snapshot and routes', middleware, 'matcher'],
  ['brand asset blocker visible', page, 'TODO: brand asset required'],
  ['brand asset blocker CSS', css, 'brand-blocker'],
  ['Korean first header', page, '한국어-first AI 회사 운영 UI'],
  ['metadata has korean locale', layout, 'lang="ko"'],
  ['OpenManus analysis architecture patterns', openManusAnalysis, '참고 가능한 아키텍처 패턴'],
  ['OpenManus analysis exclusions', openManusAnalysis, 'SoloOS에 적용하지 않을 것'],
  ['OpenManus analysis license risk', openManusAnalysis, '라이선스/저작권 리스크'],
  ['OpenManus analysis Korean cockpit translation', openManusAnalysis, '한국어 CEO cockpit에 맞게 변환할 항목'],
  ['OpenManus no direct clone statement', openManusAnalysis, '직접 복제하지 않는다'],
  ['deployment doc branding blocker', webDeployment, 'TODO: brand asset required'],
  ['README branding blocker', readme, 'TODO: brand asset required'],
];

for (const [label, source, needle] of expectations) {
  if (!source.includes(needle)) {
    throw new Error(`Missing ${label}: ${needle}`);
  }
}

if (!packageJson.scripts?.build?.includes('NODE_ENV=production')) {
  throw new Error('Build script must force NODE_ENV=production so Next middleware is not emitted with eval');
}

if (missionClient.includes('snapshot_path: SNAPSHOT_PATH')) {
  throw new Error('Mission Control API responses must not expose local SNAPSHOT_PATH');
}

console.log('static dashboard contract ok');
