# OpenManus Reference Analysis — SoloOS 적용 검토

Status: issue #1 implementation reference.  
Source checked: `FoundationAgents/OpenManus` GitHub metadata and selected public files via GitHub API only. The repository was **not cloned** into SoloOS.

## 요약

OpenManus는 범용 agent runtime에 가깝다. 핵심은 `agent loop → tool selection → tool execution → observation → next step` 구조, plan/flow 계층, 여러 도구를 한 agent에게 묶어주는 ToolCollection이다. SoloOS는 이를 그대로 복제하지 않는다. SoloOS Mission Control은 Phillip/AX Consulting 대표가 보는 한국어-first 회사 운영 cockpit이므로, 기술 로그를 앞세우는 대신 “회사 상태 / 승인 필요 / 완료 산출물 / 증거 로그”로 번역한다.

## 확인한 범위

- GitHub metadata: `FoundationAgents/OpenManus`, default branch `main`, public repo.
- Top-level structure: `app/agent`, `app/tool`, `app/flow`, `app/prompt`, `config`, `examples`, `protocol`, `tests`.
- Selected public files: README/README_ko, `app/agent/base.py`, `app/agent/toolcall.py`, `app/agent/manus.py`, `app/flow/planning.py`, `app/tool/tool_collection.py`.
- Logo/brand asset: OpenManus의 `assets/logo.jpg`는 OpenManus 자산이므로 SoloOS에 사용하지 않는다.

## 참고 가능한 아키텍처 패턴

1. **명확한 agent state machine**
   - OpenManus는 agent가 `IDLE/RUNNING/FINISHED/ERROR`류 상태를 갖고 단계별로 실행한다.
   - SoloOS 적용: Mission Control snapshot에서 AI 부서/직원 상태를 CEO용 한국어 상태(`정상 운영`, `대표 확인 필요`, `주의 필요`)로 변환한다.

2. **Plan/Flow와 Tool 실행 분리**
   - OpenManus는 planning flow와 실행 agent/tool 계층을 나눈다.
   - SoloOS 적용: “대표 요청 → CEO Office 접수 → 부서 라우팅 → 승인 → Evidence Trail” 흐름을 UI의 운영 지도와 승인함으로 표현한다.

3. **Tool registry / collection 패턴**
   - OpenManus는 여러 도구를 collection으로 모으고, tool name으로 실행한다.
   - SoloOS 적용: 구체적 tool call 노출 대신 “부서가 어떤 산출물을 만들고 어떤 증거를 남겼는지”를 보여준다.

4. **MCP/Browser/Python 등 외부 능력 연결 구조**
   - OpenManus는 MCP, browser, python, file editor 같은 capability를 agent에게 붙인다.
   - SoloOS 적용: 능력 목록은 상세 로그/부서 상세에 숨기고, CEO 화면에서는 승인 필요 여부와 결과만 우선한다.

5. **다국어 문서/README 흐름**
   - OpenManus는 README 한국어판을 제공한다.
   - SoloOS 적용: 단순 번역이 아니라 제품 자체가 한국어-first이어야 한다. 버튼, 상태, 승인 문구는 한국어를 기준으로 통일한다.

## SoloOS에 적용하지 않을 것

- OpenManus 코드를 직접 복제하지 않는다.
- OpenManus prompt/system prompt 문구를 가져오지 않는다.
- OpenManus README 문장, 데모 문구, 이미지/로고/브랜드 자산을 복사하지 않는다.
- “범용 자율 agent CLI” 제품 포지션을 그대로 따르지 않는다.
- 개발자 중심 tool call 로그를 Mission Control 첫 화면의 핵심 정보로 노출하지 않는다.
- 외부 공개 production deploy는 CEO 승인 전 진행하지 않는다.

## 라이선스/저작권 리스크

- GitHub metadata 조회에서는 license metadata가 일관되게 확인되지 않을 수 있다. README에는 MIT badge가 보이지만, SoloOS 작업 기준은 보수적으로 잡는다.
- 따라서 구조/UX 패턴만 참고하고, 소스 코드·문구·prompt·이미지·로고는 직접 복제하지 않는다.
- OpenManus의 `assets/logo.jpg` 또는 데모 미디어를 SoloOS favicon/header/README에 사용하지 않는다.
- SoloOS 문서와 UI copy는 AX Consulting 운영 맥락에 맞춰 새로 작성한다.

## 한국어 CEO cockpit에 맞게 변환할 항목

| OpenManus 계층 | SoloOS 변환 | CEO 화면 표현 |
|---|---|---|
| Agent loop | AI 부서/직원의 업무 진행 | 회사 상태, 끝난 일, 다음 액션 |
| Tool call | 부서별 실행 능력 | 상세 로그 보기 뒤에 숨김 |
| Planning flow | 대표 요청의 업무화 | 운영 흐름 지도 |
| Human ask / intervention | Phillip 승인 게이트 | 대표 승인함 |
| Observation/log | Evidence Trail | 증거 로그/감사 기록 |
| Config/API key | 운영 설정 | 배포 문서와 `.env.example`, 화면에는 노출 금지 |

## Mission Control 적용 결정

- Header는 “한국어-first AI 회사 운영 UI”를 명시한다.
- “CEO Cockpit”, “Approval Inbox”, “Evidence Trail” 같은 기존 제품 키워드는 남기되, 대표가 바로 이해하는 한국어 설명을 옆에 둔다.
- AI 부서, 승인함, 증거 로그, 상세 로그 접기 구조를 유지한다.
- repo 내 Phillip/AX Consulting 로고 asset이 없으므로, header/README/deployment doc에는 `TODO: brand asset required` blocker를 명시한다.
- production 공개 배포는 CEO 승인 전 금지한다.
