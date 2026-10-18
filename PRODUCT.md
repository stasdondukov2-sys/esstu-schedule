# ВСГУТУ — расписание

## Platform
Web / installable PWA, GitHub Pages. Responsive mobile-first product interface.

## Users and job
Confirmed by the user on 2026-10-16: the first screen prioritizes a student checking their day and nearest lesson. Teachers and room search remain available.

## Product truth
Schedules come from saved portal.esstu.ru pages; freshness remains available in More → Data and updates, while incomplete data and identity warnings remain visible. The site is an independent schedule viewer, not a claim of official university affiliation. Room occupancy means known scheduled lessons, not physical presence.

## Stack
Existing static HTML, JavaScript, compiled local Tailwind CSS; Python background synchronization/build and GitHub Actions. Preserve relative Pages URLs, offline installation and exports.

## Preserve
Group and teacher selection, current/next lesson, I/II week and day controls, subgroups, search, rooms, favorites, recent choices, notes, calendar export, session records, deep links, dark/light/system themes, source diagnostics. Keep keyboard focus containment, Escape and focus return in dialogs. Calendar swipes and sheet handles supplement visible controls. Never fabricate a room, person, schedule or date.

## Success
Nearest lesson and room can be read at a glance on a phone. The day list stays readable with long subjects and parallel lessons. On 2026-10-18 the user approved the compact reference and explicitly requested it for the actual published site: desktop retains the same centered 430px outer column, with no sidebar or floating navigation. The single header leads to group selection, subgroup, week, teacher preview and rooms; notes open from lesson cards or empty slots. Secondary tools and the overview remain in More. Reduced-motion and light/dark contrast ship with the redesign. Reference examples never replace real portal times, people or rooms.

On 2026-10-19 the user removed the full-week overview: retain I/II parity and day selection, dated schedules and session records. Consecutive online lessons must be separate cards with their own times and notes. Saved full-week preferences migrate to day mode.
