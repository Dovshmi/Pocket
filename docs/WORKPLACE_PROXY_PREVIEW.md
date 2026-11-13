# Pocket Windows Proxy/PAC Preview (v1.33.1-proxytest.1)

This is an experimental build from `experiment/workplace-pac-proxy`. **Do not merge this branch into main** until the enterprise PC test succeeds and IT policy permits this app.

## Why

On managed Windows PCs, Chrome/PowerShell may connect to HTTPS using a per-user Proxy Auto-Configuration (PAC) URL while Python's built-in `urllib.request.urlopen` tries a direct connection. A blocked direct TCP/443 connection is not proof that the HTTPS API is blocked through the approved proxy.

## What's changed

- Only **explicit DashDash** MAC and remote port POST requests are routed through the Windows native client.
- Reads the signed-in user's Windows proxy settings. If PAC/WPAD is enabled, Windows WinHTTP evaluates the corporate PAC *for the exact DashDash URL*; WinINet then sends HTTPS using that route and the Windows certificate store.
- **Never downloads PAC with Python, evaluates JavaScript, installs credentials, alters registry, disables TLS validation or falls back directly after PAC-resolution failure.**
- All local notes/commands/clipboard/subnets/local TCP checks remain unchanged.
- No automatic connectivity checks, background scanning, external synchronization or startup requests.
- Error messages include Windows WinHTTP/WinINet error codes for IT-supported troubleshooting.

## Test plan on an authorized workstation

1. Obtain the `Pocket-Portable-v1.33.1-proxytest.1.zip` from the matching GitHub **pre-release**, or the preview artifact from the Windows build workflow.
2. Exit existing Pocket completely. Make a backup of its `data` folder.
3. Extract the **whole ZIP** into a new folder and start `PocketDesk.exe`. Keep `_internal` next to the EXE. No Python or admin install required.
4. Open the MAC Lookup screen, select **DashDash**, and test only the public sample `00:1A:2B:3C:4D:5E`. The expected successful response is a non-empty vendor, similar to the browser/API.
5. If permitted, use **DashDash remote** Port Check against an authorized *public IPv4* and one TCP port. The check originates from Vercel, not your workplace.
6. Check **Local** mode still runs without internet. Do not share customer MAC/IP data to a public service.
7. If the request fails, record the exact WinHTTP/WinINet error code, and consult IT. Do not disable a corporate proxy, endpoint protection, or certificate validation.

**Limits:** A working browser or PowerShell request does not guarantee that a different EXE is allowed. Application control, proxy authentication, WinHTTP PAC compatibility, and certificate policy may still block the native client. This preview is unsigned and must be authorized by IT. `main` is untouched.

## Development/build

On the experiment branch, GitHub Actions runs unit tests on Windows, creates a PyInstaller onedir portable ZIP (containing `PocketDesk.exe`) and a standalone EXE, verifies the portable package, and uploads them as download artifacts. If permitted, it publishes a GitHub **pre-release** pointing at the experimental commit, never the stable `main` branch.
