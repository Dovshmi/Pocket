# Pocket v1.33.0 — Remote Network Tools & Smart Port Favorites

**Feature release · Windows 10/11 · Local-first · Unsigned executables**

## What's new

- **TCP port checks from two locations:** use the compact **Local / DashDash** switch to check from your PC or remotely through DashDash on Vercel. Local works with reachable IPv4/IPv6 hosts, including private LAN addresses; DashDash accepts **public IPv4 only** and checks TCP connectivity from its server.
- **Unified TCP port input:** enter up to **16 unique TCP ports** in a comma-separated list, such as `22,80,443,3389`. Duplicate entries are ignored.
- **Smart Quick Port Selection:** one expandable, compact list with **★ favorites** and the **last successfully completed check's temporary ports**. No fixed/default ports appear automatically. Temporary ports disappear after the next completed check; favorites persist. Known ports display service names, and unfamiliar ports display **Custom**.
- **One-click shortcuts:** click a quick port to add or remove it from the existing input without losing the other ports. Click ☆ / ★ to save or remove a favorite. The favorites survive restarts in the existing `data.json` file; the temporary list stays in RAM only.
- **Remote MAC vendor lookup:** switch between offline IEEE registry lookup (up to **5,000** MAC addresses) and DashDash's hosted lookup (up to **100 distinct** MAC addresses). Results support copy and CSV export.
- **Consistent layouts:** compact source switches and one combined quick-port list fit **Normal, Mini, Dashboard** and launching tools from **Extra Mini**.

## Privacy & network behavior

Local mode remains the default for both tools. **No automatic remote requests** are made when switching modes, expanding a list, or starring a port. Network requests happen only when you explicitly press **Run TCP check** or **Check vendors** in DashDash mode. In remote mode, the target IP and selected ports (or MAC addresses) are sent to `dashdash-tau.vercel.app` over HTTPS. Its current public API has no application-level authentication. Do not send sensitive target information and only test networks you have permission to assess. Offline features continue working without internet.

## Downloads

- **Pocket-Portable-v1.33.0.zip** — recommended for workplace use. Extract the full archive to a writable local directory and run `PocketDesk.exe`. Keep the `_internal` folder alongside the EXE. No Python installation is required.
- **Pocket-v1.33.0.exe** — self-contained Windows executable using the standard `%APPDATA%\\PocketDesk` data location.
- **SHA256SUMS.txt** — SHA-256 digests for both downloads.

## Upgrading

1. Fully exit Pocket, including the tray icon.
2. Back up your existing Pocket `data` folder and personalized `commands.json`.
3. Extract the Portable ZIP into a **new** folder rather than mixing versions of `_internal`.
4. Copy your backed-up portable `data` folder into the new install. Existing settings, notes, commands, and saved port preferences are preserved. Legacy Single/Selected Ports entries migrate to the new input; values exceeding the new 16-port limit must be reduced before running a check.

The release build does **not** include personal `data.json`, `commands.json`, MAC databases, passwords, backups, or private notes. GitHub Actions verifies unit tests, Windows UI layouts, packaged native modules and a clean launch from an extracted release before publishing.

**Windows security note:** binaries are unsigned. Workplace endpoint policies or antivirus may block unsigned applications. Ask your IT administrator for approval; do not bypass corporate security controls.
