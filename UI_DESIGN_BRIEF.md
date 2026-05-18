# AI Agent Control Plane — UI Design Brief
**For:** Claude Design / Figma
**Project:** Kanban-driven orchestrator for AI coding agents
**Stack:** Next.js 15, Tailwind CSS, React
**Date:** 2026-05-17

---

## Product Overview

A professional **SaaS operations dashboard** for software teams. Operators use it to spin up AI coding agents, monitor them in real time, approve or deny operations, and track costs — all from a Kanban board interface. Think Linear meets Datadog meets an AI terminal.

**Core metaphor:** Each task card is a "job ticket" assigned to an AI agent. The agent runs autonomously, streams its work log live, and the operator can watch, intervene, or stop it.

---

## Design System

### Color Palette

```
Background:    #F8FAFC  (slate-50) — page background
Surface:       #FFFFFF  (white)    — cards, panels, modals
Border:        #E2E8F0  (slate-200)
Border Dark:   #CBD5E1  (slate-300)

Text Primary:  #0F172A  (slate-900)
Text Secondary:#475569  (slate-600)
Text Muted:    #94A3B8  (slate-400)

Blue:          #2563EB  (blue-600) — primary action, CTAs
Blue Light:    #EFF6FF  (blue-50)  — selected state bg
Blue Dark:     #1D4ED8  (blue-700) — hover

Green:         #16A34A  (green-600) — success, approve, passed
Red:           #DC2626  (red-600)   — error, stop, deny, failed
Amber:         #D97706  (amber-600) — warning, approval pending
```

### Typography

- **Font:** Inter (system-ui fallback)
- **Headings:** font-semibold, slate-900
- **Body:** text-sm (14px), slate-700
- **Labels/caps:** text-xs uppercase tracking-wide, slate-500
- **Code/logs:** font-mono text-xs, green-400 on dark bg

### Spacing & Radius

- Card radius: `rounded-xl` (12px)
- Button radius: `rounded-lg` (8px)
- Badge radius: `rounded-full` (pill)
- Panel/drawer: 400px wide on desktop, full-screen on mobile

### Shadows

- Card default: `shadow-sm`
- Card hover: `shadow-md`
- Modal: `shadow-2xl`
- Panel: `shadow-xl` left edge only

---

## Screen 1: Projects List Page (`/projects`)

### Layout
Full-height page with sticky header + scrollable content area.

### Header
```
┌─────────────────────────────────────────────────────────────────┐
│  AI Agent Control Plane                    [Settings]  [New Project]
│  Orchestrate coding agents across your projects
└─────────────────────────────────────────────────────────────────┘
```
- Left: Product name (xl, bold) + tagline (sm, slate-500)
- Right: "Settings" — ghost button (border, slate-600)
- Right: "New Project" — filled blue button

### Content: Project Grid
3-column grid (responsive: 2-col tablet, 1-col mobile). Each card:

```
┌─────────────────────────────┐
│  E-commerce Platform        │
│  Full-stack Next.js store   │
│  with Stripe integration    │
│                             │
│  [main]           2h ago   │
└─────────────────────────────┘
```
- Card: white bg, rounded-xl, border slate-200, hover shadow-md, cursor-pointer
- Title: font-semibold, slate-900
- Description: text-sm slate-500, line-clamp-2
- Bottom row: branch badge (code, slate-100 bg, monospace) + relative time (xs, slate-400, right-aligned)
- Full card is a clickable link → `/projects/{id}`

### Empty State
Centered dashed border container:
```
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
  No projects yet
  [Create your first project]
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

---

## Screen 2: Kanban Board (`/projects/{id}`)

### Layout
Full-height, two-pane when task selected:
- **Left/main:** Full-width Kanban columns (shrinks when panel open)
- **Right panel:** Task detail drawer (400px, slides in from right)

### Header
```
┌─────────────────────────────────────────────────────────────────┐
│  ← Projects  /  E-commerce Platform      [Settings]  [New Task] │
└─────────────────────────────────────────────────────────────────┘
```
- Breadcrumb: "← Projects" (slate-500 link) / Project name (slate-900 bold)
- Right: Settings ghost button + New Task blue button

### Kanban Board

4 columns, horizontal scroll on overflow, each column ~280px min-width:

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  BACKLOG  4  │ IN PROGRESS 2│   REVIEW   1 │    DONE    7 │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ [task card]  │ [task card]  │ [task card]  │ [task card]  │
│ [task card]  │ [task card]  │              │ [task card]  │
│ [task card]  │              │              │ [task card]  │
│ [task card]  │              │              │ ...          │
│              │              │              │              │
│ + Add task   │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**Column header:** Column label (xs, uppercase, tracking-wide, slate-500) + count badge (rounded-full, slate-200 bg, slate-600 text)

**Column body:** White bg or very light slate, rounded-xl border, padding 12px, gap between cards 8px.

### Task Card

```
┌─────────────────────────────┐
│ ● [claude-code]             │  ← status dot + agent badge
│ Add Stripe webhook handler  │  ← title
│ Handle payment events and   │  ← description (2 lines max)
│ update order status         │
│                             │
│ ● running     3h ago       │  ← execution indicator + time
└─────────────────────────────┘
```

**Status dot (live indicator):**
- `running`: pulsing green dot (animate-pulse)
- `completed`: static green dot
- `failed`: red dot
- `stopped`: gray dot
- No execution: no dot

**Agent badge:** tiny pill, slate-100 bg — "claude-code" / "codex" / "gemini"

**Test results badge** (Sprint 3 — shown after validation):
- Passing: `✓ 12 passing` — green pill
- Failing: `✗ 3 failing` — red pill

**PR badge** (Sprint 7):
- `🔗 PR #42` — blue pill, links to GitHub

**Preview badge** (Sprint 7):
- `▶ Preview` — purple pill, links to Vercel

**Draggable:** Cards are draggable between columns (drag handle shows on hover). Drag in progress: card becomes slightly transparent + shadow.

**Click:** Opens Task Detail Panel on the right.

---

## Screen 3: Task Detail Panel (right drawer)

Slides in from right, 400px wide, full height, white bg, left border slate-200.

```
┌────────────────────────────────────────┐
│ [backlog] [claude-code]           [×]  │  ← badges + close
│ Add Stripe webhook handler             │  ← title
├────────────────────────────────────────┤
│ DESCRIPTION                            │
│ Handle Stripe webhook events, verify   │
│ signatures, update order status...     │
├────────────────────────────────────────┤
│ BRANCH                                 │
│ `task/abc123-add-stripe-webhook`       │
├────────────────────────────────────────┤
│ AGENT CONTROL                          │
│ Model: [Default (sonnet)  ▼]           │
│                                        │
│ [▶ Run Agent]     completed            │
├────────────────────────────────────────┤
│ TOKEN USAGE                            │
│ $0.0042 ─────────────── / $2.00        │  ← progress bar
│ ↑ 1,200 in   ↓ 480 out    $0.0042     │
├────────────────────────────────────────┤
│ ⚠ AGENT APPROVAL REQUIRED    4:32     │  ← amber panel (Sprint 2)
│ ┌──────────────────────────────────┐  │
│ │ Do you want to run bash command: │  │
│ │ `npm run build`? [y/n]           │  │
│ └──────────────────────────────────┘  │
│ [     Approve     ] [     Deny     ]  │
├────────────────────────────────────────┤
│ TEST RESULTS ✓ 12 passing  ✗ 0 failing│  ← Sprint 3
│ ▸ test/stripe.test.ts (12 tests)      │
├────────────────────────────────────────┤
│ EXECUTION LOG                          │
│ ┌──────────────────────────────────┐  │
│ │ > Starting claude in /workspace  │  │
│ │ > Reading Stripe docs...         │  │
│ │ > Writing webhook.ts             │  │
│ │ > Running tests...               │  │
│ │ > All tests passed               │  │
│ └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

### Execution Log Viewer
Dark terminal panel (`#0F172A` bg), monospace text, green/white output, scrollable, auto-scrolls to bottom.

Log line colors by level:
- `stdout`: `text-green-400`
- `stderr`: `text-red-400`
- `system`: `text-slate-400` italic
- `tool_use`: `text-blue-400`

Connection status bar at top of log:
- `connecting`: pulsing yellow dot + "Connecting..."
- `live`: green dot + "Live"
- `closed`: gray dot + "Session ended"
- `error`: red dot + "Reconnecting..."

---

## Component: TokenBudgetPanel

Compact card below Agent Control section.

```
TOKEN USAGE
$0.0042 ─────────▓░░░░░░░░░ / $2.00
↑ 1,200 in    ↓ 480 out         $0.0042
```

- Progress bar: blue fill, turns amber >80%, turns red when exhausted
- "Budget exhausted" red pill badge when exhausted
- Shows only when there's data (token_input > 0 or budget_usd set)

**Budget Exhausted State:**
```
TOKEN USAGE                  [Budget exhausted]
$2.00 ██████████████████████ / $2.00   (100%, red bar)
↑ 14,200 in    ↓ 6,400 out    $2.0001
```

---

## Component: ApprovalPanel (Sprint 2)

Appears between Token Budget and Execution Log when `require_approval` is on and Claude prompts for permission.

```
┌─────────────────────────────────────────┐  ← amber border (border-amber-400)
│ ● Agent Approval Required        4:32   │  ← pulsing amber dot + countdown
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ Do you want to run bash command:    │ │  ← white box, monospace
│ │ `rm -rf /tmp/build`? [y/n]         │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ [        Approve        ] [   Deny   ]  │  ← green / red buttons
└─────────────────────────────────────────┘
```

- Background: `bg-amber-50`
- Border: `border-2 border-amber-400`
- Countdown: turns red when <60 seconds remaining
- On timeout: buttons disappear, "Timed out — automatically denied" message
- Dismissed immediately after decision via WebSocket frame

---

## Component: TestResultsPanel (Sprint 3)

Shown after validation execution completes.

```
TEST RESULTS
✓ 12 passing   ✗ 0 failing              ← badges
▸ test/stripe.test.ts  (12)             ← collapsible file list
  ✓ should handle webhook event
  ✓ should verify signature
  ✓ should update order status
```

- Passing badge: green pill `bg-green-100 text-green-700`
- Failing badge: red pill `bg-red-100 text-red-700`
- Collapsible per-file list with individual test names
- "Validation running..." skeleton state while tests execute

---

## Screen 4: Settings Page (`/settings`)

Clean form page, max-w-3xl centered.

### Header
```
← Projects  /  Settings
```

### Section 1: Default Agent
3-column radio card grid:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Claude Code │  │ OpenAI Codex│  │ Gemini CLI  │
│  Selected   │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```
Selected: `border-blue-500 bg-blue-50`, others: `border-slate-200`

### Section 2: Claude Model
3 radio rows (list style):

```
◉ Claude Sonnet 4.6    Best balance of speed and capability
○ Claude Opus 4.6      Most capable, slower and more expensive
○ Claude Haiku 4.5     Fastest and most affordable
```

Selected row: `border-blue-500 bg-blue-50`

### Section 3: Budget Cap

```
$ [ 2.00 ] USD
Recommended: $2–$5 for most tasks
```

Number input with $ prefix and USD suffix, range 0.10–100, step 0.50.

### Section 4: Safety & Approval (Sprint 2)

```
Require Human Approval
[toggle switch]  When enabled, an approval popup appears in the task
                 panel for each agent operation. Auto-denied after
                 5 minutes of no response.
```

Toggle switch: blue when on, slate when off. Smooth slide animation.

### Section 5: API Keys

Two key input rows (OpenAI, Gemini):

```
OpenAI API Key  (for Codex CLI)           ● Key saved
[sk-••••••••••••••••••] [Show] [Clear]

Gemini API Key  (for Gemini CLI)
[AIza...                ] [Show]
```

- Masked input by default (type="password")
- "● Key saved" green indicator when set
- "Show/Hide" toggle button
- "Clear" danger button (red border) when key is saved

### Section 6: Deployment (Sprint 7)

```
GitHub Integration
GitHub Token      [••••••••••••••••••] [Show] [Clear]
Repository        [owner/repo-name   ]

Vercel Integration
Vercel Token      [••••••••••••••••••] [Show] [Clear]
Project ID        [prj_xxxxxxxxxxxx  ]

Auto Deploy
[toggle]  Automatically deploy to Vercel after tests pass
```

### Save Bar (sticky bottom)

```
[error message or "Settings saved" success]        [Save Settings]
```
- Floats at page bottom inside a white card
- "Settings saved" text is green, fades after 3s
- Error text is red

---

## Screen 5: Create Project Modal

Centered modal with backdrop blur.

```
┌────────────────────────────────────────┐
│ New Project                       [×]  │
├────────────────────────────────────────┤
│ Project Name *                         │
│ [E-commerce Platform            ]      │
│                                        │
│ Description (optional)                 │
│ [Full-stack Next.js store...    ]      │
│                                        │
│ Repository Path *                      │
│ [/Users/arun/projects/shop      ]      │
│ Absolute path to a local git repo      │
│                                        │
│ Default Branch                         │
│ [main                           ]      │
├────────────────────────────────────────┤
│ [          Cancel          ] [Create]  │
└────────────────────────────────────────┘
```

- Backdrop: `bg-black/50 backdrop-blur-sm`
- Modal: white, rounded-xl, shadow-2xl, max-w-lg
- Required fields marked with `*`
- Helper text in slate-400 below inputs

---

## Interaction Patterns

### Drag and Drop (Kanban)
- Drag handle (⋮⋮) appears on card hover, cursor changes to `grab`
- Dragging card: `opacity-60`, `cursor-grabbing`, slight scale-up `scale-105`
- Drop target column: highlighted with `border-blue-300 bg-blue-50/50`
- Optimistic update: card moves immediately, reverts on API error with shake animation

### Status Transitions (visual feedback)
- Task card: execution status dot pulses when `running`
- Execution controls: button swaps Run ↔ Stop based on live status
- Connection status in log: live dot when WS open

### Loading States
- Project list: 3 skeleton cards (pulse animation)
- Task detail panel: skeleton lines for each section
- Log viewer: "Connecting..." spinner then live stream

### Error States
- API errors: red toast notification (top right, 4s timeout)
- Execution failed: red card border + "failed" badge
- Network lost: yellow banner "Reconnecting to agent..."

---

## Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Mobile (<640px) | Single column Kanban (horizontal scroll), panel is full-screen overlay |
| Tablet (640–1024px) | 2-column Kanban, panel slides over 50% width |
| Desktop (>1024px) | 4-column Kanban, panel is 400px sidebar |

---

## Animations & Motion

- Panel slide in: `translateX(100%) → translateX(0)`, 200ms ease-out
- Card hover: `shadow-sm → shadow-md`, 150ms
- Modal appear: `scale(0.95) opacity-0 → scale(1) opacity-1`, 150ms
- Approval panel entrance: `translateY(-4px) opacity-0 → none`, 200ms
- Budget bar fill: `width` transition 500ms ease
- Status dot pulse: CSS `animate-pulse` (1.5s infinite)
- Token counter: count-up animation when value changes

---

## Figma Component Checklist

### Atoms
- [ ] Badge (status colors: backlog/in_progress/review/done/pending/running/completed/failed/stopped)
- [ ] Agent badge (claude-code / codex / gemini pill)
- [ ] Status dot (running pulse / completed / failed / none)
- [ ] Toggle switch
- [ ] Button (primary blue / ghost / danger)
- [ ] Input (text / password / number)
- [ ] Avatar/icon for each agent type

### Molecules
- [ ] Task card (all states: default, running, completed, failed, with badges)
- [ ] Column header (label + count)
- [ ] Token budget bar (empty / partial / near-limit / exhausted)
- [ ] Log line (by level: stdout / stderr / system / tool_use)
- [ ] Connection status indicator
- [ ] Settings toggle row

### Organisms
- [ ] Project card
- [ ] Kanban column (with task stack + add button)
- [ ] Task detail panel (all sections assembled)
- [ ] Approval panel
- [ ] Test results panel
- [ ] Settings form section
- [ ] Create project modal
- [ ] Save bar

### Pages
- [ ] Projects list (with projects / empty state / loading)
- [ ] Kanban board (no panel / with panel / dragging state)
- [ ] Settings (all sections expanded)

---

## Key UX Principles

1. **Operators are watching, not waiting** — live streaming and real-time status are primary; polling is a fallback
2. **Confidence over ambiguity** — every operation has clear status (running dot, error badge, budget bar)
3. **Intervention is easy** — Stop button always visible during execution; approval panel is unmissable
4. **Cost is always visible** — token/cost display in panel when any execution is active
5. **Dense but not cluttered** — use space efficiently; operators may have many tasks open across multiple monitors

---

## Reference Screenshots to Create

1. **Projects list** — 6 project cards in a grid, one card hovered
2. **Kanban board** — 4 columns with tasks, one task selected with panel open
3. **Task running** — panel showing live log stream + token budget bar + pulsing "running" state
4. **Approval popup** — amber approval panel mid-execution
5. **Post-completion** — panel showing test results badge + completed status
6. **Settings page** — all sections visible, Safety & Approval toggle ON
7. **Mobile board** — single column view, panel as full-screen overlay
