---
name: "ВСГУТУ — Compact Liquid Glass"
description: "Компактная стеклянная лента реального расписания с контекстными панелями."
colors:
  light-campus-bg: "#f3f5f5"
  light-campus-ink: "#182321"
  light-campus-muted: "#4c5c58"
  light-campus-glass: "rgba(255,255,255,.9)"
  light-campus-panel: "#fff"
  light-campus-line: "#d5dfdb"
  light-campus-control: "#eaf0ed"
  light-campus-accent: "#00634b"
  light-campus-solid: "#006b50"
  light-campus-accent-soft: "#e0f2e9"
  light-campus-focus: "#006b50"
  light-campus-warning: "#764607"
  light-cyber-current: "#008260"
  light-cyber-current-ink: "#006047"
  light-cyber-current-bg: "#edf9f2"
  light-cyber-next: "#8b5cf6"
  light-cyber-next-ink: "#6434ad"
  light-cyber-next-bg: "#f7f2ff"
  light-cyber-card: "rgba(255,255,255,.9)"
  light-cyber-past: "#56635f"
  dark-campus-bg: "#000"
  dark-campus-ink: "#f8fafc"
  dark-campus-muted: "#bcc5d2"
  dark-campus-glass: "rgba(13,16,22,.92)"
  dark-campus-panel: "#101218"
  dark-campus-line: "rgba(255,255,255,.1)"
  dark-campus-control: "rgba(255,255,255,.045)"
  dark-campus-accent: "#50dbb1"
  dark-campus-solid: "#087958"
  dark-campus-accent-soft: "rgba(16,185,129,.12)"
  dark-campus-focus: "#6ee7b7"
  dark-campus-warning: "#f4cb8e"
  dark-cyber-current: "#10b981"
  dark-cyber-current-ink: "#6ee7b7"
  dark-cyber-current-bg: "rgba(12,22,19,.76)"
  dark-cyber-next: "#8b5cf6"
  dark-cyber-next-ink: "#c5b3ff"
  dark-cyber-next-bg: "rgba(18,14,28,.74)"
  dark-cyber-card: "rgba(15,15,20,.7)"
  dark-cyber-past: "#929aa9"
  light-liquid-ink: "#37475c"
  light-liquid-tint: "rgba(94,110,128,.065)"
  light-liquid-top: "rgba(255,255,255,.95)"
  light-liquid-bottom: "rgba(255,255,255,.77)"
  light-liquid-edge: "rgba(255,255,255,.95)"
  light-liquid-shadow: "rgba(36,47,69,.08)"
  light-liquid-room-ink: "#37475c"
  light-liquid-room-bg: "rgba(94,110,128,.1)"
  dark-liquid-ink: "#cbd5e1"
  dark-liquid-tint: "rgba(148,163,184,.06)"
  dark-liquid-top: "rgba(30,34,43,.66)"
  dark-liquid-bottom: "rgba(8,10,16,.88)"
  dark-liquid-edge: "rgba(255,255,255,.34)"
  dark-liquid-shadow: "rgba(0,0,0,.7)"
  dark-liquid-room-ink: "#e2e8f0"
  dark-liquid-room-bg: "rgba(148,163,184,.18)"
  practice-ink: "#ddd0ff"
  lab-ink: "#fde68a"
  lecture-ink: "#fecdd3"
  light-practice-ink: "#6133a3"
  light-lab-ink: "#704c05"
  light-lecture-ink: "#a02847"
  current-room-ink: "#022c22"
  current-room-fill: "#6ee7b7"
  light-current-room-ink: "#003b2c"
  light-current-room-fill: "#a5f3cf"
  error: "#fda4af"
  light-error: "#9f1239"
  replica-practice-ink: "#ede9fe"
  replica-lab-ink: "#fef9c3"
  replica-lecture-ink: "#ffe4e6"
  replica-current-tag-ink: "#d1fae5"
  replica-current-room-top: "#a7f3d0"
  replica-current-room-mid: "#34d399"
  replica-current-room-bottom: "#10b981"
  replica-practice-fill: "rgba(139,92,246,.24)"
  replica-lab-fill: "rgba(234,179,8,.24)"
  replica-lecture-fill: "rgba(244,63,94,.2)"
  replica-current-fill: "rgba(16,185,129,.22)"
typography:
  body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  lesson:
    fontFamily: "Inter, sans-serif"
    fontSize: "15.5px"
    fontWeight: 750
    lineHeight: 1.35
    letterSpacing: "-.018em"
  hero-subject:
    fontFamily: "Inter, sans-serif"
    fontSize: "1.125rem"
    lineHeight: 1.45
  room:
    fontFamily: "Inter, sans-serif"
    fontSize: "2rem"
    fontWeight: 650
  label:
    fontFamily: "Inter, sans-serif"
    fontSize: ".75rem"
    fontWeight: 650
    lineHeight: 1.4
  time:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: ".75rem"
    fontWeight: 600
  room-chip:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: ".75rem"
    fontWeight: 650
  sheet-title:
    fontFamily: "Inter, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-.02em"
rounded:
  card: "22px"
  header-control: "16px"
  day: "16px"
  input: "16px"
  sheet: "28px"
  type: "8px"
  pill: "999px"
spacing:
  card: "13px"
  agenda-gap: "10px"
  day-gap: "6px"
  sheet: "16px"
components:
  button-primary:
    backgroundColor: "{colors.dark-campus-solid}"
    textColor: "{colors.light-campus-panel}"
    rounded: "9px"
    height: "44px"
  button-glass:
    textColor: "{colors.dark-campus-ink}"
    rounded: "{rounded.header-control}"
    height: "32px"
  search-field:
    backgroundColor: "{colors.dark-campus-control}"
    textColor: "{colors.dark-campus-ink}"
    rounded: "{rounded.input}"
    padding: "10px 13px"
    height: "48px"
  lesson-card:
    textColor: "{colors.dark-campus-ink}"
    rounded: "{rounded.card}"
    padding: "{spacing.card}"
  room-chip:
    typography: "{typography.room-chip}"
    rounded: "{rounded.pill}"
    padding: "2px 11px"
  day-pill:
    rounded: "{rounded.day}"
    padding: "7px 1px"
  footer-navigation:
    padding: "20px 2px 0"
    typography: "{typography.label}"
  teacher-search-field:
    backgroundColor: "{colors.dark-campus-control}"
    textColor: "{colors.dark-campus-ink}"
    rounded: "{rounded.input}"
    padding: "10px 12px"
    height: "42px"
  type-chip:
    rounded: "{rounded.type}"
    padding: "2px 10px"
    typography: "{typography.label}"
  sheet:
    backgroundColor: "{colors.dark-campus-glass}"
    rounded: "{rounded.sheet}"
    padding: "{spacing.sheet}"
---

# Design System: ВСГУТУ — Compact Liquid Glass

## Overview

**Creative North Star: "Compact Liquid Glass"**

Black glass, a static silver ambient wash and glossy upper bevels make the real day schedule a compact stack. The approved reference supplies material and narrow composition; actual portal data supplies dates, people, rooms and uncertainty. Light mode keeps the same geometry with pale glass and darker ink.

The current system is the final cascade of styles/campus.css, styles/liquid.css and styles/replica.css, with local fonts and utilities in styles/input.css. static/replica.js adapts the existing service-backed interface. Context stays close to the selected lesson, teacher or room.

**Key Characteristics:**
- One narrow agenda column on phones and desktop.
- Neutral glass bodies with silver bevels and categorical borders, shadows and labels.
- Emerald current state and room with independently meaningful lesson-type labels.
- Contextual bottom sheets, truthful source status and keyboard alternatives.

## Colors

### Primary

Emerald marks the active day, current lesson state, current room and important actions. The current room uses the three replica-current-room gradient stops. Its pair number uses replica-current-tag-ink over replica-current-fill. Progress runs from dark emerald toward mint. Current status remains textual as well as chromatic.

### Secondary

Violet practice, amber laboratory and rose lecture distinguish category borders, shadows, room droplets and labels. Replica type inks and fills record the final dark labels; inherited light type inks remain active in light mode. Current card framing and room use emerald while lesson labels keep their real category. Mixed and parallel slots preserve each child's actual identity.

### Neutral

Dark canvas remains true black, with near-white ink and cool grey secondary text. Light mode uses pale grey, white glass and green-grey ink. The final agenda body gradient is neutral glass, including current and categorised cards: state/type border and shadow carry the surrounding colour. Preview cards retain their own neutral control fill. Legacy campus, cyber and liquid primitives stay because inherited controls, light surfaces, source notices and the overview consume them; they are aliases within this world.

**The State With Meaning Rule.** Current framing and room may turn emerald; the lesson-type label must retain the actual category and readable text.

## Typography

Inter is locally hosted variable text (100–900) with platform fallbacks. JetBrains Mono is locally hosted (400–700) for times, calendar numerals and room chips. Cyrillic and Latin subsets use font-display: swap; licences ship with the fonts.

The compact subject uses the lesson role. Teacher, time, day, type and freshness labels predominantly use (12px); some supporting preview rows use (11px). Sheet headings use (15px); sheet search/editor fields remain (16px). The inherited overview keeps its own larger type inside More. Agenda subjects clamp to two lines; opening the card or subject opens the note sheet with the full subject, source and metadata. Merged online blocks retain native disclosure.

**The Meaning Survives Density Rule.** Compact presentation keeps full subjects, parallel lessons, source warnings and text labels available.

## Layout

The agenda keeps the approved (430px) outer composition and maximum (402px) content width on desktop and phone. Header and main use width:min(402px,calc(100% - 28px)); the main begins (5px) below the header. At (360px) and below they use calc(100% - 20px). Header controls occupy one row; six day pills, one source-status chip, the lesson stack and a quiet footer follow. The approved first screen has no sidebar, hero or floating navigation.

Cards use (13px) padding and (10px) gaps. Days have (6px) gaps and (46px) minimum height. At the narrow breakpoint single-lesson rooms return to normal flow. Header controls and footer buttons use (32px) minimum height; sheet buttons use at least (36px). Other inherited actions retain their own sizes. These are observed compact dimensions rather than a universal touch-target claim.

All overlays align to the bottom. Sheets cap at (430px) width and (88dvh) height, with (16px) padding and internal scrolling. Group selection, teacher search, rooms and notes are four primary sheets. More retains secondary tools, week controls and the overview. Footer links to the source portal and teachers and opens More. Update banners share the content cap and reserve bottom space when visible.

## Elevation & Depth

Dark cards use a radial reflection, layered neutral gradient, bright inset upper bevel, darker lower edge and diffuse shadows. Practice, laboratory, lecture and current states retain coloured borders and shadows over that final neutral body. Cards blur at (28px) with (185%) saturation; day pills blur at (20px), liquid pills at (24px). Sheets have a separate near-opaque dark gradient, top edge and upward shadow over a (4px) blurred overlay.

The sidecar records exact shadow recipes. Reduced transparency replaces major cards and sheets with the opaque campus panel and removes blur. Inherited unsupported-backdrop styling supplies a card fallback. Ambient light remains static.

**The Material Has Edges Rule.** Keep the upper highlight, darker lower edge and translucent body together; flat tint alone does not reproduce this world.

## Shapes

Lessons, empty slots and preview cards share the (22px) silhouette. Header pills, directory rows and fields use (16px); pair/type chips use (8px); preview timeline rows use (12px). Room droplets and filter chips are fully rounded. Sheets use (28px) upper corners and square lower corners on every screen. Empty slots have a dashed border and restrained inset depth.

## Components

### Buttons and fields

Glossy header controls combine a silver upper edge with glass fill. Filled actions use the campus solid accent; the full-schedule action has (16px) corners. Teacher search is at least (42px) high with (10px 12px) padding. Other search fields retain inherited geometry, while all sheet fields use (16px) text. Inherited campus focus outlines remain visible. Pointer feedback and reduced-motion alternatives stay available.

### Day pills and type chips

Six actual days display dates and categorical dots with real accessible counts. Active selection combines emerald fill, border and inset shine. Type chips retain explicit labels and category-specific dark inks/fills inside current cards.

### Cards and room droplets

Agenda lesson sections have independent actions: the card or subject opens a note sheet containing the full subject, source and metadata. Teacher names open teacher previews; physical room droplets open room details. Only merged online blocks retain native disclosure. Online labels remain informational. Notes preview below the summary. Clock-driven current status and progress appear only on the matching date/week. Past cards use the approved faded neutral treatment: whole-card opacity (.62), increasing to (.85) on hover. Keep text readable in this intentionally quiet reference treatment.

Empty slots preserve actual source times, explain subgroup availability where known and open slot notes. Parallel records retain separate labels, people and rooms.

### Contextual sheets and footer

Teacher search combines department filters, directory rows, a selected-teacher day timeline and an explicit full-schedule action. Rooms combine known-building filters and room timelines; occupancy means known scheduled lessons. Map links search known building notation. Notes keep slot context, room/teacher actions and source details. The in-flow footer keeps source, teachers and More reachable without a floating bar.

Sheets retain focus containment, Escape, focus return and visible close controls. Existing pointer entry takes (200ms); keyboard opening and day/week changes remain immediate. Card feedback takes (220ms), days (200ms), liquid pills (180ms). Reduced motion disables movement. Skeleton pulsing remains limited to loading.

## Do's and Don'ts

### Do:
- **Do** preserve truthful source status, real dates, lesson categories and room identities.
- **Do** retain the narrow agenda geometry on desktop and phone.
- **Do** use local Inter and JetBrains Mono for their established roles.
- **Do** retain access to full lesson/source details, focus, light mode and reduced-motion/transparency alternatives.

### Don't:
- **Don't** import demonstration schedules, invent floors or addresses, or infer physical occupancy.
- **Don't** restore a sidebar, hero above the agenda or floating navigation to the approved first screen.
- **Don't** repaint current lesson-type labels emerald or replace source warnings with colour alone.
- **Don't** flatten the bevel or add continuous ambient animation.
