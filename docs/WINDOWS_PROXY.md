# Windows proxy, direct HTTPS and IEEE updates (Pocket development)

Pocket is offline-first. In **Settings → Network connection → Use Windows Proxy**, choose the transport for explicitly requested online checks. **ON is the default** for both new and upgraded profiles. The setting is stored locally and applies to the next request.

| Operation | Proxy ON | Proxy OFF |
| --- | --- | --- |
| DashDash MAC Lookup | Existing user PAC/WPAD + native WinINet HTTPS POST | Explicit direct HTTPS POST |
| DashDash remote TCP checks | Existing user PAC/WPAD + native WinINet HTTPS POST | Explicit direct HTTPS POST |
| Update IEEE DB | Windows PAC + WinINet HTTPS GET | **Direct native WinINet HTTPS GET**, Windows trust store, no PAC |
| Local MAC/TCP checks | Offline / local | Offline / local |
| EN/HE keyboard correction | Offline | Offline |

## The successful DashDash corporate proxy transport is unchanged

The Windows DashDash POST transport remains as before in pocket/windows_proxy_urlopen.py. It reads the signed-in user's proxy settings through WinHttpGetIEProxyConfigForCurrentUser, resolves PAC/WPAD for the destination with WinHttpGetProxyForUrl and sends WinINet HTTPS using the Windows trust store and user authentication. It does not edit Windows proxy settings, evaluate PAC JavaScript locally, disable TLS verification, or silently fall back to direct access after PAC failure.

In Proxy OFF mode, **DashDash** uses its explicit direct urllib opener with ProxyHandler({}), avoiding Windows/environment proxy discovery. **IEEE downloads now use a separate direct native WinINet HTTPS GET**, selecting INTERNET_OPEN_TYPE_DIRECT instead of resolving PAC/WPAD. This uses Windows certificate trust rather than Python's SSL verification path. No global proxy settings are changed, and neither route disables certificate validation.

## IEEE MAC vendor database

The **Update IEEE DB** button downloads only these four official HTTPS registries:

- https://standards-oui.ieee.org/oui/oui.csv
- https://standards-oui.ieee.org/oui28/mam.csv
- https://standards-oui.ieee.org/oui36/oui36.csv
- https://standards-oui.ieee.org/iab/iab.csv

IEEE downloads use a new, dedicated WinINet **GET** transport rather than the small-response, POST-only DashDash transport. Each CSV is size-limited and validated; the local vendor database is atomically replaced only after all downloads and parsing succeed. Previous local data stays intact on failures. No MAC input values are sent to IEEE by this operation.

When Proxy is OFF on Windows, IEEE downloads use WinINet's explicit **direct** connection mode and Windows TLS validation. This is intended to resolve Python's `CERTIFICATE_VERIFY_FAILED` on PCs with a Windows-trusted HTTPS inspection certificate. If the certificate is not trusted by Windows either, download will still fail safely with a WinINet certificate error; ask IT to verify the root certificate. We do not accept self-signed certificates or disable verification automatically. The existing manual **Import CSV** action stays available. IEEE may still reject automated requests (HTTP 403 or 429) regardless of the selected route.

## Troubleshooting

- Enable **Use Windows Proxy** when operating on a managed Windows computer with corporate PAC/WPAD.
- Verify the approved website in your browser; browser success does not guarantee that the app is approved.
- Capture WinHTTP/WinINet errors without sharing customer data or credentials.
- A failing direct TCP/443 test does not prove an HTTPS proxy path is unavailable.
- Local TCP checks run on your computer; DashDash TCP checks run remotely on Vercel, support public IPv4 only, and should be used on authorized targets.
- Switching the setting does not initiate network traffic.

These features are currently on the development branch; v1.36.0 remains the last published stable release until a separate release is approved.
