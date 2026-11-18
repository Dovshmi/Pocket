# Pocket v1.39.9 — Reminders (development)

**Work in progress, not published.** The latest public release remains v1.39.8.

## Features

- **Own Reminders icon and expandable Mini navigation:** Mini retains the original eight fixed-width icon **positions** in its first row. With seven tools and Settings, the last More icon opens Settings directly as before. When Reminders (or more future tools) is enabled, the last icon changes to a **More / Less** expander. Clicking More displays additional icon rows of up to eight positions; with the current defaults, the second row contains only **Reminders** and **Settings**. Clicking Less collapses them; the first row does not move. Reminders also appears in the Normal and Dashboard tool menus and can be hidden in Visible tools.
- **Compact, themed calendar and time:** The Note scheduler has been reduced from **425×522 to 366×445 pixels** and uses the user's selected Pocket palette rather than a light calendar. Day selection, 00–23 hours and 00–59 minutes remain available. Quick times are in one **Dropdown**: Custom time, +15 minutes, +1 hour or Tomorrow 09:00. Selecting a preset automatically sets the date/time and **disables (greys) the manual hour/minute fields**. Returning to Custom or clicking a calendar date re-enables them.
- **Pocket-themed reminder dialog:** A small modal reminder opens at the scheduled time even if Pocket's main window is hidden. Windows' basic Yes/No MessageBox cannot contain text input, so this uses native Tk/ttk controls matching the current Pocket theme.
- **Timestamped, opt-in response:** Until **Add response** is checked, the input is disabled and cannot accept typing or paste. If checked and nonblank on Done/Dismiss/Escape/close, the Note gets a new block at the **very bottom**: local **DD/MM/YYYY HH:MM** on its own line, followed by the customer's response on the next line. The existing Note text is preserved byte-for-byte. If unchecked or blank, the Note body is not changed.
- **Snooze:** Postpone by 5, 15, 30 or 60 minutes. Draft text and checkbox state are retained across Snooze and restart, without appending until the user dismisses the reminder with response enabled.
- **Reminders overview:** Upcoming, Snoozed and Completed counts, status filter, per-Note cards, Open, Edit time, Snooze 15m and Done. Buttons are split over short rows to fit Mini width. This is a dedicated icon/menu rather than a shortcut embedded in Settings.
- **Safety:** Showing a reminder does not mark it complete. If Pocket is restarted before an answer, the reminder will reappear. Failed local saves roll back the in-memory change; an unsent draft requires confirmation before being discarded from the overview.
- **Offline-first:** No sign-in, external DB, internet calls or additional dependencies.

## Tests

Run Python unit tests, the new desktop reminder smoke test, and the existing Mini/Dashboard/Normal UI regressions. CI runs Windows and Linux tests. The portable build is checked but no v1.39.9 release is published by this development workflow.

## Release policy

Continue working on branch **feature/v1.39.9-reminders** until explicit user instruction. Do not tag/publish a release or sync unfinished changes into main.
