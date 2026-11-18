# Pocket v1.39.9 — Reminders (development)

**Work in progress, not published.** The latest public release remains v1.39.8.

## Features

- **Unchanged Mini navigation:** The original eight icons (Notes, Links, Ports, MAC, CLI, Subnet, Clip, More) keep the exact original order, width, and positions. Reminders is a subpage accessible via **More → Settings → Reminders: Open** and **Notes → Reminders**. No ninth icon is added.
- **Calendar and time selection:** Select a day on a month calendar, hour 00–23 and minute 00–59, or shortcuts for +15m, +1h or Tomorrow 09:00. Times use the Windows computer's local timezone, and Pocket must be running in the tray.
- **Windows-style reminder dialog:** A regular decorated modal reminder dialog opens at the scheduled time even when Pocket's main window is hidden. Windows' standard Yes/No MessageBox does not support custom input fields, so the reminder uses native-looking Tk/ttk controls.
- **Add response is optional:** When the checkbox is not selected, the text input is **disabled**—users cannot enter anything. When enabled, Done, Dismiss, Escape or closing the window append the response to the **bottom of the original Note**, only when nonempty. Unchecked or blank input never changes the note body.
- **Snooze:** Postpone by 5, 15, 30 or 60 minutes. Draft text and checkbox state are retained across Snooze and restart, without appending until the user dismisses the reminder with response enabled.
- **Reminders overview:** Upcoming, Snoozed and Completed counts, status filter, per-Note cards, Open, Edit time, Snooze 15m and Done. Buttons are split over short rows to fit Mini width.
- **Safety:** Showing a reminder does not mark it complete. If Pocket is restarted before an answer, the reminder will reappear. Failed local saves roll back the in-memory change; an unsent draft requires confirmation before being discarded from the overview.
- **Offline-first:** No sign-in, external DB, internet calls or additional dependencies.

## Tests

Run Python unit tests, the new desktop reminder smoke test, and the existing Mini/Dashboard/Normal UI regressions. CI runs Windows and Linux tests. The portable build is checked but no v1.39.9 release is published by this development workflow.

## Release policy

Continue working on branch **feature/v1.39.9-reminders** until explicit user instruction. Do not tag/publish a release or sync unfinished changes into main.
