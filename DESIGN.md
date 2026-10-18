---
name: "ВСГУТУ — Stealth Cyber-Glass"
description: "Обсидиановое расписание с изумрудной текущей и фиолетовой следующей парой."
colors:
  dark-bg: "#050507"
  dark-ink: "#f3f5f8"
  dark-muted: "#a7b2c3"
  current: "#10b981"
  next: "#8b5cf6"
  glass: "rgba(15,15,20,.7)"
  light-bg: "#f3f5f5"
  light-ink: "#182321"
  light-current: "#008260"
typography:
  body: "Inter, locally hosted variable WOFF2 with Cyrillic and Latin subsets"
  time: "ui-monospace; tabular numerals"
rounded:
  card: "14px"
  control: "12px"
---

# Stealth Cyber-Glass

User-approved reference: stealth_cyber_glass.html, supplied 18 October 2026.
Mode: Operate. Preserve real source data, incomplete-source warnings, filters,
notes, teachers, rooms, offline use and keyboard operation.

## Visual language

AMOLED #050507 background with faint emerald/violet ambient gradients. Dark
obsidian cards use a 1px border and 12px backdrop blur, with opaque fallbacks.
The current lesson gets an emerald outline, subtle glow, countdown and progress;
the next visible lesson gets a violet outline and countdown. The chosen reference
explicitly earns these neon accents. Inter is served locally with its OFL licence;
there are no runtime font or CSS CDN requests.

## Composition

One compact header row: group selector, campus date/week, SVG search and settings.
The group is the sole h1. Search controls have distinct accessible names.
The page has no repeated brand/title banner. Desktop keeps a 300px nearest-lesson
column and a flexible agenda; mobile stacks them with compact spacing. The agenda
uses standalone 14px lesson cards and a dashed break row. Each time range is
inline, while subject, teacher, lesson type and room remain readable.

Styles live in styles/stealth.css, after the shared campus layout. Light theme has
its own ink, card and state colours. Inputs, selection, scrollbars, focus outlines,
dialogs and bottom navigation inherit the same tokens. Touch actions stay at
least 44px. Native details retain the full subject, source details and notes.

## State contract

visualPairStates derives current/next/past from the selected campus date, the
actual start/end times and the active lesson filter. The end is exclusive;
seconds advance progress. During a break there is no current pair and the next
visible slot stays violet. A different future day and ambiguous dated sessions
never receive a fabricated current/next state. Existing clock updates set the
classes directly; no MutationObserver watches or reparses visible text.

Past lessons use quieter, contrasting text rather than whole-card opacity or
pointer-events:none. Users can still read, expand and annotate them. Adjacent
online lessons retain their original entries and controls inside the disclosure.
Current/next are labelled in words as well as colour. Source warnings and the
single freshness chip remain visible. Reduced motion and opaque glass fallbacks
are preserved.

## Verification

Check 320px mobile and desktop, both themes, every lesson state and the break
boundary. Exercise notes on a past lesson, selection/filter changes, teacher and
room search, dialogs, offline loading and worker upgrades. Use axe and rendered
pixel contrast checks; a screenshot alone does not establish accessibility.
