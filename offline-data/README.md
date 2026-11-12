# Offline reference files for PocketDesk

Copy these two JSON files into the `data/` folder next to `PocketDesk.exe`
when running the **Pocket-Portable** release:

- `commands.json`: the complete curated Pocket CLI command library (573 commands).
- `vendors.json`: offline MAC manufacturer registrations (IEEE MA-L, MA-M,
  MA-S and IAB), exported for Pocket v1.32.2.

Close PocketDesk before replacing either file, and back up any existing edited
`commands.json` first. Do **not** overwrite `data.json`, which stores notes and
settings. Reopen the application to load the new reference files.

The MAC vendor cache matches the public `vendors.json` asset published in
[the v1.32.2 GitHub release](https://github.com/Dovshmi/Pocket/releases/tag/v1.32.2).
Its source is the public IEEE registration data available from an open mirror.

**Public data warning:** This directory is visible to everyone because the
GitHub repository is public. Do not add private passwords, keys, operational
configurations, customer identifiers, or private notes here.
