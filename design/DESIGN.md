# kiwi knows — design system

An internal knowledge companion for Samsung Life. RAG over policies, codebases, and operational logs.

This document captures the visual language. Every value lives in `assets/styles.css` as a CSS variable — change it there, everything follows.

---

## Brand

**Wordmark** — `kiwi knows`, set in *Instrument Serif* at 30px, weight 400, letter-spacing -0.02em. Always lowercase. The serif intentionally clashes with the technical content; that contrast is the point.

**Mark** — the kiwi bird (`assets/kiwi.svg`). A round-bodied, two-legged silhouette in cobalt-blue with a marigold beak and two black eyes. Use it small (22–32px) in the topbar, medium (56–64px) on the login card and chat empty state. The bird is used as-is — do not recolor.

**Favicon** — same SVG file, declared via `<link rel="icon" type="image/svg+xml">`.

**Tagline** — *An internal knowledge companion*. Set in serif italic.

---

## Color

The palette is a warm-paper neutral with one accent. Cool SaaS blues are explicitly avoided.

| Token              | Hex       | Use                                       |
|--------------------|-----------|-------------------------------------------|
| `--kk-bg`          | `#F5F1E8` | Page background. Warm cream.              |
| `--kk-bg-warm`     | `#EFEADF` | Sidebars, secondary surfaces.             |
| `--kk-panel`       | `#FBF9F3` | Cards, primary panels.                    |
| `--kk-panel-2`     | `#FFFFFF` | Inputs, elevated surfaces.                |
| `--kk-ink`         | `#1A1815` | Primary text, primary buttons.            |
| `--kk-ink-2`       | `#2A2722` | Body text.                                |
| `--kk-muted`       | `#6B6760` | Secondary text.                           |
| `--kk-muted-2`     | `#908B82` | Tertiary text, hints.                     |
| `--kk-line`        | `rgba(26, 24, 21, 0.08)` | Hairlines.                  |
| `--kk-accent`      | `#6B8E4E` | Kiwi green. Cited refs, success state.    |
| `--kk-accent-deep` | `#4F6B38` | Hover accent, citation text.              |
| `--kk-accent-soft` | `#E8EFD8` | Citation chips, soft fills.               |
| `--kk-warn`        | `#B97A2A` | Reindex pending, attention.               |

The kiwi green is the *only* color used for affirmative state. There is no blue.

---

## Typography

Three families do specific work:

- **Instrument Serif** (serif) — wordmark, page titles, card titles, large numerals in stats. Italic is used for editorial emphasis (greetings, taglines, in-prose emphasis).
- **Geist** (sans) — all UI: labels, buttons, body, navigation.
- **Geist Mono** (mono) — endpoints, hashes, latencies, line counts, every machine-shaped token.

### Scale

| Role         | Family       | Size | Weight | Notes                            |
|--------------|--------------|------|--------|----------------------------------|
| Display      | Serif        | 76px | 400    | Index hero only.                 |
| Page title   | Serif        | 44px | 400    | Admin page header.               |
| Empty title  | Serif        | 52px | 400    | Chat empty state.                |
| Card title   | Serif        | 24px | 400    |                                   |
| H2           | Sans         | 16px | 600    | Inside document preview.         |
| Body         | Sans         | 14px | 400    | Default.                         |
| UI           | Sans         | 13px | 500    | Nav, buttons, sidebar entries.   |
| Caption      | Sans         | 12px | 400    | Field labels.                    |
| Eyebrow      | Sans         | 10px | 500    | Uppercase, 0.12em tracking.      |
| Mono         | Mono         | 12px | 400    | Endpoints, counts, hashes.       |

All sans text uses `letter-spacing: -0.005em` and `font-feature-settings: 'ss01', 'cv11'` for tighter, more confident rendering.

---

## Shape & spacing

- **Radii** — `6px` (controls), `10px` (cards), `14px` (large cards, login card), `20px` (composer).
- **Hairlines** — all internal borders are `rgba(26,24,21,0.08)` to `0.14`. Never use a 1px black border.
- **Shadows** — three tiers: `sm` (hairline-only), `md` (8px Y, -8px blur), `lg` (24px Y, -20px blur). Cards default to `sm`; floating elements use `md`; the login card uses `lg`.
- **Density** — UI sits on a 4/8 grid. Cards have 22-24px padding. Forms use 14px gap.

---

## Components

### Buttons
- **Primary** — ink fill, cream text. Used once per surface.
- **Ghost** — white fill, hairline border, ink text. Used for secondary actions.
- **Icon button** — 28×28, transparent, fills on hover with `--kk-bg-warm`.

### Inputs
38px tall by default. Focus ring is `0 0 0 3px rgba(26,24,21,0.06)` plus a darkened border. No blue, no shadow puff.

### Citations
A cited claim ends in `<sup class="kk-cite">N</sup>` — kiwi-green bg, mono digit. The cited sources block lives directly under the assistant message, listing title + topic + a confidence bar (kiwi-green fill) + numeric score.

### Status dots
7px circle with a 3-4px opaque halo of the same color. Three states: ok (green), warn (warm orange), neutral (grey).

### Nav pill (topbar)
A horizontal pill containing the three views (Chat / Sources / Admin). Active item is a solid ink pill with cream text. No underlines, no carets.

---

## Voice

- Mix of Korean and English is natural — `약관 v3.2`, `kk-api`, `IFRS17 CSM 계산 로직`. Don't force translation.
- Concise. Avoid empty modifiers ("powerful", "intuitive").
- Editorial moments (login tagline, chat empty greeting) lean on serif italic and full sentences. Functional UI is terse.

---

## File map

```
index.html                  # Single entry point; loads React + Babel.
DESIGN.md                   # This file.
assets/
  kiwi.svg                  # Bird mark — also serves as favicon.
  styles.css                # Every visual token. Edit here.
src/
  app.jsx                   # Top-level: auth gate + view router.
  components/
    kiwi-mark.jsx           # <KiwiMark>, <Icon>
    topbar.jsx              # Topbar with brand + nav + user.
  screens/
    login.jsx               # Email + password → onLogin.
    chat.jsx                # Sessions sidebar + thread + composer.
                            #   Live: window.claude.complete()
                            #   with a system prompt locking the assistant
                            #   to the Samsung Life RAG domain.
    sources.jsx             # 3-pane: rail + doc list + split editor.
                            #   Markdown source ↔ live preview.
    admin.jsx               # Runtime config + live health + usage.
```

State persists to `localStorage` (`kk.auth`, `kk.view`) — refresh resumes where you left off. Sign out from the user pill in the topbar clears it.

---

## What's interactive

| Where                | What you can actually do                                    |
|----------------------|-------------------------------------------------------------|
| Login                | Type anything → enters the app. State persists.             |
| Topbar               | Switch Chat / Sources / Admin. Brand returns to chat. Avatar signs out. |
| Chat sidebar         | Click sessions, create new chat, search box live filters.   |
| Chat starters        | Click → sends the prompt directly.                          |
| Chat composer        | Type & send. `⌘↵` sends. Live response from Claude.         |
| Cited sources        | Hover styles only (citations are illustrative).             |
| Sources rail         | Topic filter narrows the doc list. Tabs are UI-only.        |
| Sources doc list     | Click switches the editor. Filter input live-narrows.       |
| Sources editor       | Edit markdown → preview re-renders. Edit title in-place.    |
| Admin form           | All fields editable. Reset restores defaults.               |
| Admin health         | "Check health" updates the timestamp.                       |
| Admin save           | Save flashes a confirmation.                                |

---

## Implementation notes for handoff

- **No build step.** Everything is plain JSX run through Babel-standalone. Production should swap to a Vite/Next bundle — the file layout maps 1:1.
- **Components share scope via `window.*`** because Babel-standalone gives each `<script>` its own closure. When migrating to a bundler, switch to ES module `export`/`import`.
- **Markdown rendering is intentional and minimal** (bold, italic, code, lists, citation refs). For production, swap to `marked` or `react-markdown` with the same CSS tokens.
- **Real LLM call** lives in `chat.jsx` → `send()`. The system-prompt is short and domain-locked. Swap in your own endpoint by replacing the `window.claude.complete` call — the response handling is unchanged.
