---
name: "ВСГУТУ — Dark Liquid Glass"
description: "Чёрное стекло, глянцевые грани и читаемое расписание с честными состояниями."
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
typography:
  body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  lesson:
    fontFamily: "Inter, sans-serif"
    fontSize: ".9375rem"
    fontWeight: 750
    lineHeight: 1.4
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
    fontSize: "1.25rem"
    fontWeight: 600
    letterSpacing: "-.02em"
rounded:
  card: "22px"
  header-control: "18px"
  day: "16px"
  input: "16px"
  nav: "24px"
  nav-item: "17px"
  sheet: "28px"
  type: "7px"
  pill: "999px"
spacing:
  card: "15px"
  card-mobile: "13px"
  agenda-gap: "10px"
  day-gap: "6px"
  columns: "24px"
  sheet: "24px"
  sheet-mobile: "20px"
components:
  button-primary:
    backgroundColor: "{colors.dark-campus-solid}"
    textColor: "{colors.light-campus-panel}"
    rounded: "9px"
    height: "44px"
  button-glass:
    textColor: "{colors.dark-campus-ink}"
    rounded: "{rounded.header-control}"
    height: "44px"
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
    padding: "2px 10px"
  day-pill:
    rounded: "{rounded.day}"
    padding: "9px 1px"
  floating-nav:
    rounded: "{rounded.nav}"
    padding: "7px"
  sheet:
    backgroundColor: "{colors.dark-campus-glass}"
    rounded: "{rounded.sheet}"
    padding: "{spacing.sheet}"
---

# Design System: ВСГУТУ — Dark Liquid Glass

## Overview

**Creative North Star: "Dark Liquid Glass"**

True black, a static neutral ambient wash and glossy bevels turn the timetable into compact glass objects. This world follows the user's pinned ai_studio_code.html and replaces Stealth Cyber-Glass. Its material serves a working schedule: source uncertainty, room identity and long subjects remain readable.

The shipped source is styles/liquid.css after styles/campus.css, with local fonts, utility adjustments in styles/input.css, and card/day markup in static/simple-ui.js. Dark and light themes share geometry with separate inks and glass. Final dark mobile, desktop and light mobile captures show the implementation; their visible test-clock state is not a claim about the live schedule.

**Key Characteristics:**
- Black glass with bright upper bevels and darker lower edges.
- Type-tinted cards, informational room droplets and compact mono numerals.
- Emerald current state, readable neutral past state and truthful source status.
- Glossy controls and sheets with keyboard, motion and transparency alternatives.

## Colors

### Primary

Emerald handles selection and current lessons. Current cards override their type material, room fill and ink; progress uses emerald-to-mint. Next-state aliases remain violet, but do not universally repaint a next card: its lesson type still controls material/labels. The overview's next border and status use next aliases.

### Secondary

Violet practice, amber laboratory and rose lecture tint the bevel, room droplet and type chip. Light mode uses darker type inks. Calendar dots carry matching categorical hues with actual counts available to assistive technology. Text labels remain present.

### Neutral

Dark canvas is true black with near-white ink and cool grey secondary text. Light canvas is pale grey with green-grey ink and white glass. Mixed, unknown and review card materials remain neutral, while parallel children preserve distinct labels/rooms. Past cards and all child labels/rooms become neutral without whole-card opacity.

**The State Before Type Rule.** Current emerald and past neutral override categorical tint. A mixed card never invents a dominant lesson type; preserve each actual label.

Frontmatter keys preserve source token names with light/dark prefixes. The inherited --cyber-* aliases are legacy names still consumed by this world, not a separate visual identity. In particular --cyber-card/current-bg/next-bg remain declared, but final card backgrounds come from liquid gradients; record the final cascade rather than treating old background aliases as active material. --cyber-past supplies past ink. The --liquid-rgb channels are type/state dependent, not fixed global colours.

## Typography

Inter is locally hosted variable text (100–900); JetBrains Mono is locally hosted (400–700) for times, calendar dates and room chips. Cyrillic and Latin WOFF2 subsets use font-display: swap. Both fonts ship SIL OFL licences in static/fonts/. Large overview room text remains Inter.

Closed lesson titles clamp to two lines; opening the native disclosure reveals the full subject. The overview subject becomes (1rem) and room (1.5rem) on mobile, using frontmatter sizes on desktop. Form text stays (1rem). Functional labels and global 10px/11px text utilities use a (.75rem / 12px) minimum. Sheet headings use the title role; ordinary headings do not gain decorative emoji.

**The Readable Past Rule.** Quiet past text remains readable, expandable and annotatable. Never fade the complete card.

## Layout

The desktop shell caps at (1120px), with a sticky (300px) left summary and flexible agenda separated by (24px). At (850px) the column shrinks to (260px) and gap to (20px). At (700px) and below, agenda comes first and summary follows below the lessons; shell side margins are (14px). Header, week selector, six day pills, selected date and one source-status chip lead into the agenda.

Cards use (15px) padding, (13px) on mobile, with (10px) agenda gaps. At (360px) and below room badges return to normal flow to avoid time collisions. Controls retain at least (44px) touch height; navigation actions use (52px). Long subjects and room strings wrap. Fixed bottom navigation respects the safe area and page bottom padding keeps content reachable.

## Elevation & Depth

Radial type tint, a layered glass gradient, bright inset upper bevel and darker lower edge create the liquid surface. Soft chromatic and black shadows supply depth. Room droplets use a smaller bevel/shadow. Dark cards derive the upper gradient from type RGB at (.12) alpha; past cards use a restrained neutral upper surface. These are diffuse material shadows rather than hard offsets.

Cards, day pills and group control use (28px) blur with (185%) saturation where supported; inherited sheets/navigation use (22px) blur. Reduced transparency substitutes the opaque panel and disables blur on major surfaces; unsupported card backdrop filtering also gets an opaque fallback. Readability must survive without transparency.

**The Material Has Edges Rule.** Keep the upper highlight, darker lower edge and translucent body together; flat tint alone does not reproduce this world.

## Shapes

Lesson and overview cards use the card radius. Header controls, day pills, navigation/items and type/number chips retain their distinct radii in frontmatter. Rooms/countdowns are pills. Sheets use (28px) corners on desktop and top corners only on mobile; fields use (16px). Existing banners, dialogs and utility buttons keep their own shapes: (22px) is not a universal overlay radius.

## Components

Glossy global controls combine a reflective upper edge with glass fill. Filled sheet actions use the solid accent. Pointer press scales to (.98) with (120ms) feedback; colour/border changes take (160ms). Visible focus uses a (2px) outline with (2px) offset; text fields use zero offset. Disabled buttons retain their wait cursor and opacity.

Six day pills show dates/type dots and expose real counts. Selection is emerald border/soft fill plus inset shine. Lesson cards use native disclosure for source, teacher/room actions and notes. The room droplet is informational. Current text, countdown and progress accompany colour; past cards retain actions. Adjacent online entries preserve original disclosures.

The fixed three-action navigation keeps Schedule highlighted while tool sheets open. Sheets retain focus containment, Escape and focus return; mobile handles supplement visible controls. Existing pointer sheet entry takes (200ms), from opacity (.5), translateY (12px) and scale (.985); keyboard opening and day/week changes remain immediate. Reduced motion disables transitions/animations. Ambient wash is static; loading skeletons may pulse at (1.5s) when motion is allowed. The declared drawer easing token has no current consumer.

## Do's and Don'ts

### Do:
- **Do** preserve truthful source status, dates, lesson types and room identities.
- **Do** use local Inter text and JetBrains Mono for compact functional numerals.
- **Do** retain native disclosure, keyboard focus and readable light/opaque/reduced-motion states.

### Don't:
- **Don't** import demo timetable data or infer occupancy beyond known scheduled lessons.
- **Don't** fade past cards or present informational room droplets as standalone navigation.
- **Don't** flatten the bevel, add continuous ambient animation, or apply card corners to every overlay.
- **Don't** replace text labels or source warnings with colour alone.
