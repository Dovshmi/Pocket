# Pocket v1.40 — Release readiness checklist

**Candidate:** `experiment/extra-excel-lookup` (not yet stable `main`).
**Automated verification:** `.github/workflows/mini-checks.yml` on Windows/Linux Python 3.11/3.13, GUI integration checks, and real Windows portable EXE smoke. All CI tests use synthetic profiles and mock Office objects, not confidential work data.

## Required manual acceptance on the intended Windows workstation

Use a fresh portable ZIP in a **new directory**. Quit the previous Pocket process, back up `data/`, and copy only `data/` to the new `Pocket-Portable/` directory. Never mix `_internal/` files from different builds.

- [ ] **Show/Hide state:** Open Settings → Show / Hide immediately below Appearance. Enabled tools have **green icons** and a minus (Hide) action; disabled tools have **red icons** and a plus (Add) action.
- [ ] **Hide/restore:** Hide a real tool and verify its data is untouched. Add it from Settings or Mini Plus and confirm it appears **last** in the toolbar.
- [ ] **Mini layout:** Drag icons into a new order. Confirm that the order persists after closing/reopening Pocket and after a Settings backup/restore. Settings can move but cannot be hidden.
- [ ] **More/Plus boundary:** With seven active menus and some hidden, Plus is the last tile. With eight or more, More occupies tile eight and Plus appears last in the expanded row. With all tools active, Plus disappears.
- [ ] **Extra Matches:** Search for more than five results. Wheel over MATCHES scrolls Pocket's outer page without changing the list's viewport; the slim right scrollbar scrolls results. Up/Down changes the selected hit; Left/Right changes Selected Row.
- [ ] **Local vs offline:** Local search can read an authorized Excel workbook; Database search works offline from an existing local SQLite index. Sync starts **only** when pressed, and failed/cancelled sync does not destroy the old database.
- [ ] **Excel (same file):** Open Workbook A, then click its Pocket shortcut again. Confirm the same Excel workbook is activated, with **no duplicate**.
- [ ] **Excel (different file):** With Workbook A open, click a Pocket shortcut to Workbook B. Confirm B opens and A stays open. Repeat when B is already open.
- [ ] **Excel permissions:** If workbooks are protected, verify normal Office authorization prompts and absence of unexpected writes or workbook saves.
- [ ] **Outlook SOC:** Choose a real selected result, open a draft, and verify name/line/FortiGate IP/VDOM are correct (or explicitly marked missing). Contact, phone, expert approval name, issue and prior incident are editable. Verify that Pocket **does not send**.
- [ ] **Regression:** Notes, Reminders, Clipboard, Commands, Shortcuts, network tools, proxy settings, Quick Slots, PIN, tray shortcut and app startup still work as before.
- [ ] **Data/privacy:** Confirm that the offline SQLite copy and backups are permitted under company policy. They are **not encrypted**. No corporate source workbook or SQLite file belongs in a public GitHub release.

## Promotion criteria

Promote to `main` only after the latest GitHub Actions run is green and the above checks pass on the target workstation. Recommended: squash the experimental change history into a reviewed v1.40 merge, update the official stable README/badge/download links, tag v1.40.0, publish official Windows ZIP/EXE with checksums, and retain v1.39.9 for rollback. The experimental preview release/workflow can be excluded or archived when preparing the stable merge.

The CI test suite cannot validate real enterprise Office COM, Windows shell foreground restrictions, live network/proxy permissions, or local organizational data-protection approvals. Mark those checks separately.
