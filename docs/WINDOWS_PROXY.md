# Windows corporate proxy and PAC support (Pocket v1.33.1)

Pocket normally works offline. The only DashDash connections are explicit HTTPS POST requests made when the user selects **DashDash** in MAC Lookup or TCP Port Check and presses the action button.

## How it works

On Windows, Pocket reads the signed-in user's Internet proxy configuration using `WinHttpGetIEProxyConfigForCurrentUser`. If an automatic proxy script (PAC) or WPAD is configured, Windows resolves the route for the **specific DashDash HTTPS URL** using `WinHttpGetProxyForUrl`. Pocket then sends the request using the Windows WinINet HTTPS stack and Windows certificate store. If no proxy is configured, the Windows configuration determines direct access.

Pocket does **not** modify system proxy settings, write credentials, evaluate PAC JavaScript itself, disable certificate validation, ignore HTTP redirects, or fall back to a direct connection when PAC resolution fails. Requests do not run in the background, at startup, or merely when switching Local/DashDash.

This is **not a bypass** of corporate security; organizational policy and endpoint controls still apply. A browser working does not guarantee that Pocket will be allowed.

## Troubleshooting (read-only)

- Open the DashDash URL in an approved browser.
- Test your own approved DashDash MAC lookup with a public sample address (`00:1A:2B:3C:4D:5E`).
- If Pocket fails, capture the exact **WinHTTP** or **WinINet** error code and ask IT to review approved proxy/application controls.
- `Test-NetConnection <hostname> -Port 443` tests **direct** TCP/443 and can fail even when browser HTTPS via a proxy succeeds.

Use **Local** for tests of internal networks and when offline. DashDash remote TCP checks originate from Vercel and accept only a *public IPv4* address; the DashDash API is public. Do not send customer or sensitive target information without authorization.

## Packaging

The stable release includes a Portable ZIP with `PocketDesk.exe` and an `_internal` folder, plus a separate standalone Windows EXE. Extract the whole ZIP before starting it and back up your personal `data` directory when upgrading. Windows application-control approval may be required for unsigned executables.
