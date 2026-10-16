# ВСГУТУ — расписание

## Platform
Web / installable PWA, GitHub Pages. Responsive mobile-first product interface.

## Users and job
Confirmed by the user on 2026-10-16: the first screen prioritizes a student checking their day and nearest lesson. Teachers and room search remain available.

## Product truth
Schedules come from saved portal.esstu.ru pages; freshness, incomplete data and identity warnings must remain visible. The site is an independent schedule viewer, not a claim of official university affiliation. Room occupancy means known scheduled lessons, not physical presence.

## Stack
Existing static HTML, JavaScript, compiled local Tailwind CSS; Python background synchronization/build and GitHub Actions. Preserve relative Pages URLs, offline installation and exports.

## Preserve
Group and teacher selection, current/next lesson, I/II week and day controls, subgroups, search, rooms, favorites, recent choices, notes, calendar export, session records, deep links, dark/light/system themes, source diagnostics. Keep keyboard focus containment, Escape and focus return in dialogs. Calendar swipes and sheet handles supplement visible controls. Never fabricate a room, person, schedule or date.

## Success
Nearest lesson and room can be read at a glance on a phone. The day list stays readable with long subjects and parallel lessons. Desktop uses available width. Secondary tools remain discoverable without crowding the schedule. Reduced-motion and light/dark contrast ship with the redesign.
