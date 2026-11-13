# Pocket v1.33.1 — Windows Proxy/PAC Support

**Stable maintenance release · Windows 10/11 · Portable ZIP and standalone EXE**

## What's fixed

- **DashDash remote MAC and TCP checks now work with Windows-managed corporate proxy configurations**, including automatically configured PAC/WPAD policies, when permitted by the network.
- Requests to `dashdash-tau.vercel.app` use the signed-in user's Windows proxy settings and the native Windows HTTPS stack instead of relying solely on Python urllib's direct network route.
- Errors include meaningful WinHTTP/WinINet codes when Windows cannot resolve the proxy or complete the request.
- No hard-coded proxy addresses or passwords, no TLS certificate-validation bypass, no registry changes and no direct fallback after PAC-resolution failure.

## Behavior retained

- **Local remains the default** for both MAC Vendor Lookup and TCP Port Check.
- Windows PAC handling is used **only for manually started DashDash requests**. Notes, commands, shortcuts, clipboard, templates, subnet calculations and local checks are unchanged.
- DashDash remote checks still send the selected MACs or public IPv4/ports to the public DashDash API. Remote TCP results describe connectivity **from Vercel**, not from the user's PC.
- Offline mode continues to work without an internet connection, account, background scanning or telemetry.

## Validation

- Regression tests pass on Windows/Linux; both normal GUI and packaged Windows UI startup have been checked.
- A user verified that the preview build's DashDash network feature works in a managed workplace proxy environment.
- Windows endpoint-security policies may still block unsigned executables on other computers; confirm permission with IT.

## Download

- **Pocket-Portable-v1.33.1.zip** — complete portable Windows package with `PocketDesk.exe`, `_internal` DLL/Python runtime, and integrity manifest.
- **Pocket-v1.33.1.exe** — standalone Windows executable.
- **SHA256SUMS.txt** — checksums for the ZIP and EXE.

## Safely upgrade

1. Fully **Exit Pocket**, including from the Windows notification area.
2. Back up your existing `data/` folder (portable) or `%APPDATA%\\PocketDesk\\` (standalone), especially private `commands.json`.
3. Extract the new ZIP into a **separate new folder**; never mix old `_internal/` files with the new build.
4. Copy only your personal `data/` folder into the new portable folder, and confirm notes, commands, and settings are preserved.
5. Test DashDash MAC lookup with public sample `00:1A:2B:3C:4D:5E`. Keep local mode for local/private-network targets.

**Privacy:** release archives contain only public example commands and application assets. No user passwords, private command libraries, clipboard history, or personal work data are included. Binaries are unsigned; follow organization application-control policy.
