---
version: alpha
name: AX Consulting Mission Control
description: CEO-readable dark operations cockpit for SoloOS and AX Consulting.
colors:
  primary: "#08090A"
  secondary: "#111216"
  tertiary: "#5E6AD2"
  neutral: "#F7F8F8"
  surface: "#15161A"
  surfaceStrong: "#1D1F26"
  text: "#F7F8F8"
  textSoft: "#D0D6E0"
  textMuted: "#8A8F98"
  line: "#2A2D35"
  success: "#10B981"
  warning: "#FBBF24"
  danger: "#F97373"
typography:
  display:
    fontFamily: Inter
    fontSize: 4.75rem
    fontWeight: 650
    lineHeight: 0.96
    letterSpacing: "-0.065em"
  h1:
    fontFamily: Inter
    fontSize: 3rem
    fontWeight: 650
    lineHeight: 1.08
    letterSpacing: "-0.055em"
  h2:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: 650
    lineHeight: 1.12
    letterSpacing: "-0.052em"
  body-lg:
    fontFamily: Inter
    fontSize: 1.1875rem
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "-0.01em"
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.58
  label:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.15em"
  mono:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: 500
    lineHeight: 1.45
rounded:
  sm: 12px
  md: 16px
  lg: 24px
  pill: 999px
spacing:
  xs: 6px
  sm: 10px
  md: 14px
  lg: 22px
  xl: 34px
  xxl: 56px
components:
  page-background:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text}"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    padding: 24px
  panel-strong:
    backgroundColor: "{colors.surfaceStrong}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    padding: 26px
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: 12px
  status-success:
    backgroundColor: "{colors.success}"
    textColor: "#06120D"
    rounded: "{rounded.pill}"
    padding: 8px
  status-warning:
    backgroundColor: "{colors.warning}"
    textColor: "#171004"
    rounded: "{rounded.pill}"
    padding: 8px
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textSoft}"
    rounded: "{rounded.lg}"
    padding: 22px
  audit-row:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.textMuted}"
    rounded: "{rounded.md}"
    padding: 14px
  evidence-card:
    backgroundColor: "{colors.surfaceStrong}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.md}"
    padding: 18px
  risk-alert:
    backgroundColor: "{colors.danger}"
    textColor: "#180506"
    rounded: "{rounded.md}"
    padding: 14px
  divider:
    backgroundColor: "{colors.line}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    height: 1px
---

## Overview

AX Consulting Mission Control is a calm, high-signal operations cockpit for a solo CEO running an AI-native company. The interface should feel like Linear-quality command software: dark, precise, quiet, evidence-first, and never decorative for decoration's sake.

The design translates technical SoloOS state into CEO language: status, completed work, decision needed, next action, and evidence. Every screen should answer: "오늘 회사가 어떻게 돌아가고 있나요?"

## Colors

- **Primary (#08090A):** Near-black operating-room background. Use for the page base.
- **Secondary (#111216):** Deep charcoal gradient stop for visual depth.
- **Tertiary (#7170FF):** SoloOS intelligence accent. Use for labels, primary actions, active states, and subtle glows.
- **Success (#10B981):** Healthy workflow / completed evidence. Use sparingly so green remains meaningful.
- **Warning (#FBBF24):** CEO approval, risk, or blocked external action.
- **Text (#F7F8F8), Soft (#D0D6E0), Muted (#8A8F98):** Three-level hierarchy for headline, explanation, and metadata.
- **Line (#2A2D35):** Low-contrast borders. Avoid bright white outlines.

## Typography

Use Inter for the interface and JetBrains Mono only for IDs, audit snippets, paths, and machine-readable evidence. Headlines should be large, tight, and slightly compressed with negative letter spacing. Body copy should be readable and CEO-friendly, not log-like.

## Layout

Use a centered shell with max width around 1180px. The main page starts with a CEO answer card, then mission metrics, then operational panels. Prefer cards and grids that disclose detail progressively. Put engineering logs behind sections such as "상세 로그 보기".

Spacing should be generous enough to reduce cognitive load:

- 34px top shell padding on desktop
- 14px grid gaps for dense cockpit sections
- 22–26px card padding
- 56px bottom breathing room

## Elevation & Depth

Use glass-like dark panels with subtle borders and blur, not heavy shadows. Depth should communicate hierarchy while preserving a sober command-center feel. Accent glows are allowed only around key status indicators and hero gradients.

## Shapes

Cards use 24px radii. Inner rows use 16px radii. Avatars use 15px radii. Pill labels use full rounding. Avoid sharp enterprise SaaS rectangles unless showing raw audit data.

## Components

- **CEO Answer Card:** The first screen element. It states current business status in one sentence and includes a simple status signal.
- **Mission Metric Card:** Short label, large number, one-line interpretation.
- **Agent Row:** Avatar, department name, current mission, status. Do not expose raw prompts.
- **Approval Panel:** Warning-toned card for actions that need Phillip's decision.
- **Evidence Panel:** Audit paths, DB counts, generated artifacts, or verification outputs. Keep details collapsible.
- **Primary Button:** Indigo fill with white text. Use only for actions that move CEO workflow forward.

## Do's and Don'ts

Do:

- Start from the CEO question before technical detail.
- Make next action obvious.
- Preserve auditability and evidence.
- Keep color usage restrained and meaningful.
- Validate generated UI in browser and check console errors.

Don't:

- Turn the dashboard into a developer log stream.
- Use generic AI gradients without operational meaning.
- Hide approval/risk states.
- Commit secrets, customer private data, or MCP credentials.
- Treat Stitch output as production-ready without code review and tests.
