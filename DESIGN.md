---
name: "ВСГУТУ — Campus Glass"
description: "A calm glass schedule interface with an immediately readable nearest lesson and room."
colors:
  graphite: "#10131d"
  ink: "#f1f2f8"
  muted: "#b2b9cd"
  glass: "rgba(29,33,48,.82)"
  panel: "#1c2030"
  line: "rgba(213,219,255,.15)"
  control: "rgba(205,214,255,.07)"
  lavender: "#cfbfff"
  solid: "#7252be"
  accent-soft: "rgba(169,135,247,.17)"
  focus: "#d5c7ff"
  warning: "#f4cb8e"
  light-bg: "#eef0f6"
  light-ink: "#252a3b"
  light-muted: "#4d586b"
  light-glass: "rgba(255,255,255,.84)"
  light-panel: "#f9faff"
  light-line: "rgba(64,72,100,.17)"
  light-control: "rgba(87,94,129,.075)"
  light-accent: "#6140a8"
  light-solid: "#6846af"
  light-accent-soft: "#ece6f8"
  light-focus: "#6b46b5"
  light-warning: "#86510a"
typography:
  room:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'
    fontSize: "40px"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-.035em"
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.03em"
  title:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.32
    letterSpacing: "-.025em"
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'
    fontSize: "14px"
    lineHeight: 1.5
  lesson:
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.45
rounded:
  panel: "16px"
  control: "10px"
  calendar: "11px"
  chip: "6px"
  nav: "18px"
  nav-item: "12px"
  sheet: "20px"
spacing:
  nav-inset: "8px"
  hero-inset: "24px"
  agenda-inset: "24px 26px"
  column-gap: "30px"
  mobile-hero-inset: "22px"
  mobile-agenda-inset: "20px 18px"
components:
  button-primary:
    backgroundColor: "{colors.solid}"
    textColor: "#fff"
    rounded: "9px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.control}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "0 18px"
    height: "44px"
  glass-panel:
    backgroundColor: "{colors.glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
  room-chip:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.lavender}"
    rounded: "{rounded.chip}"
    padding: "4px 7px"
  floating-nav:
    backgroundColor: "{colors.glass}"
    rounded: "{rounded.nav}"
    padding: "{spacing.nav-inset}"
    width: "390px"
  search-field:
    backgroundColor: "{colors.control}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "44px"
---

# Design System: ВСГУТУ — Campus Glass

## Overview

**Creative North Star: "Campus Glass"**

The user chose a dark schedule interface with a glass effect. Graphite, translucent panels and muted lavender support a calm, practical student tool. The nearest lesson and its room supply the strongest visual emphasis; this is an operating screen with real schedule data.

The system remains usable in light and system themes and without transparency. Freshness, source uncertainty and incomplete data remain readable parts of the interface. This document records source implementation in `styles/campus.css`, `static/index.html`, `static/simple-ui.js` and `static/accessibility.js`; it does not claim independent visual or contrast verification.

**Key Characteristics:**
- Dark graphite canvas with restrained lavender emphasis.
- Large room typography and a compact readable day agenda.
- Translucent bordered surfaces with opaque fallbacks.
- Quiet state changes and immediate keyboard interaction.

## Colors

The palette combines cool graphite neutrals with a soft lavender accent; light theme uses the paired light tokens in the frontmatter. CSS custom properties in `styles/campus.css` are the implementation source of truth; the frontmatter captures their current values.

### Primary
- **Lavender:** status, room links and current selection text.
- **Solid violet:** filled actions and the selected I/II week control, with white text.
- **Soft lavender:** selected day, navigation item and small status backgrounds.

### Secondary
- **Warning amber:** source problems, incomplete data and scheduled building changes. It supplements text, never replaces it.

### Neutral
- **Graphite:** app canvas; **Ink:** primary content; **Muted:** timestamps and supporting labels.
- **Glass:** major surfaces; **Panel:** opaque fallback and toast surface.
- **Line:** quiet separators; **Control:** fields and neutral controls.

**The Truth Stays Visible Rule.** Never use low contrast or decoration to hide data age, saved/offline delivery, incomplete parsing or ambiguous teacher identity.

## Typography

Use the platform system sans-serif stack in the frontmatter. There are no external font downloads. Times, dates and remaining minutes use tabular numerals where specified in CSS.

The room role is the signature display treatment; it increases to 43px on mobile. The page headline reduces to 28px on mobile. Hero subjects retain the title role, while agenda subjects reduce to 14px. Supporting labels range from 10–13px; the smallest current-state badge is 8px and is supplementary, not the sole indicator of a current lesson.

Long subjects wrap with `overflow-wrap:anywhere`; avoid shrinking them or forcing a single line. Keep room identifiers as source strings rather than inventing a shorter number.

## Layout

The current schedule screen uses a maximum 1120px container with 32px side clearance, a sticky header and a two-column grid: a 340px overview and flexible agenda, separated by 30px. At 850px and below, the overview becomes 285px and the gap 20px. At 700px and below, the layout stacks, the overview stops sticking, and the container has 16px side clearance. The 360px breakpoint reduces clearance to 12px.

The overview precedes the agenda in DOM order. The agenda combines I/II week selection, six equal day controls and time-aligned lesson rows. Parallel lessons remain inside the same time slot. Secondary functions live in dialogs and the More menu.

The floating navigation has three actions: Расписание, Поиск, Аудитории. Its width is capped by the viewport, and its bottom offset respects safe-area insets. Body bottom padding (116px) reserves space for it. This composition describes the schedule screen; new surfaces should inherit the visual language without copying this grid mechanically.

## Elevation & Depth

Depth comes from tonal layers, fine borders and restrained ambient radial gradients behind the app. The main hero explicitly has no shadow. Glass panels, header, navigation and simple dialog sheets use a 22px backdrop blur where supported. A dark overlay separates dialogs from the background.

**The Readable Glass Rule.** Glass must stay readable without blur. Reduced-transparency preferences use the opaque panel token and disable blur; unsupported backdrop filtering also uses the opaque panel. Never depend on a background image for contrast.

Notes and dynamically created room dialogs share the same simple-sheet and overlay classes. Legacy utility names can remain in markup, but Campus Glass overrides define their canonical surface. This source scan does not independently establish complete visual parity of every secondary state.

## Shapes

Major surfaces use the panel radius. Controls are more compact, chips have a smaller curve, and navigation and dialog sheets have their own larger curves from the frontmatter. Thin borders and spacious internal padding establish the surface shape. Lesson rows share separators within the agenda rather than becoming individual floating cards.

## Components

### Buttons and fields

Buttons, including the week selector, use a 44px minimum height. Primary actions use solid violet and white text; neutral actions use the control surface. Focus-visible uses a 2px focus outline with a 4px offset. Fine-pointer hover changes background or text; active press scales to .98. Inputs and textareas use the accent caret, and placeholder text uses the muted token. Disabled buttons reduce opacity and display a waiting cursor.

### Nearest lesson and day rows

The hero displays current or next lesson metadata, subject, teacher/groups and a large clickable room only when a room can be decoded. It preserves parallel lessons. A progress indicator uses `scaleX` during a current lesson. Clock updates preserve the hero's content node while the lesson is unchanged, protecting keyboard focus. Dated session records and incomplete sources do not receive a fabricated current lesson.

Day rows use native details/summary for expanded metadata, notes, teacher and room actions. Lesson-type dots supplement written type labels. Missing data and a known empty day use distinct messages.

### Selection and navigation

Day and week buttons expose selected state with `aria-pressed`; today's calendar day also uses `aria-current="date"`. The floating navigation keeps the schedule item visually selected; search and rooms launch dialogs rather than changing the underlying route selection.

### Dialogs and motion

Simple sheets are centered with a 560px maximum width on desktop (620px for search) and become bottom-aligned on mobile. They remain scrollable within 88dvh, increasing to 90dvh on mobile. Opening a simple sheet by pointer uses a 220ms entrance with opacity and a 12px translation / .985 scale, using the CSS ease-out curve. Keyboard opening is immediate. Closing is immediate. The focus stack contains keyboard focus, makes background content inert, supports Escape, and returns focus to the launcher or its replacement.

**The Quiet Schedule Rule.** Frequent day/week switches and clock ticks do not animate content entrances. Reduced motion disables button transitions, press scaling and dialog entrances. General button state transitions use 160ms for color and border and 120ms for press transforms. The drawer easing token exists in CSS but no documented component currently consumes it.

## Do's and Don'ts

### Do:
- **Do** keep source status and warnings readable alongside the schedule.
- **Do** use the existing system font and let long subject names wrap.
- **Do** preserve native details, selected-state semantics and dialog focus behavior.
- **Do** verify dark, light, opaque fallback and reduced-motion states when extending components.

### Don't:
- **Don't** animate frequent day changes or delay keyboard dialog access.
- **Don't** fabricate rooms, dates or a current lesson when source data cannot establish them.
- **Don't** introduce blur-dependent readability or promote legacy dialog shadows into the canonical surface style.
- **Don't** replace functional warnings with color-only signals.
