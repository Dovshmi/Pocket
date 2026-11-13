"""Network transport selection tests. No live network access or PAC downloads."""
import io
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.request import Request

from pocket import windows_proxy_urlopen as transport


class ProxyTransportTests(unittest.TestCase):
    def setUp(self):
        self.request = Request(
            "https://dashdash-tau.vercel.app/api/mac-lookup",
            data=b'{"macs":["00:1A:2B:3C:4D:5E"]}',
            method="POST",
        )

    def test_non_windows_uses_existing_urllib_transport(self):
        response = object()
        with patch.object(transport.os, "name", "posix"), patch.object(
            transport, "_stdlib_urlopen", return_value=response
        ) as urllib:
            self.assertIs(transport.urlopen(self.request, timeout=7), response)
        urllib.assert_called_once_with(self.request, timeout=7)

    def test_windows_selects_native_transport_not_urllib(self):
        response = object()
        with patch.object(transport.os, "name", "nt"), patch.object(
            transport, "_windows_urlopen", return_value=response
        ) as native, patch.object(
            transport, "_stdlib_urlopen", side_effect=AssertionError("do not bypass PAC")
        ):
            self.assertIs(transport.urlopen(self.request, timeout=9), response)
        native.assert_called_once_with(self.request, 9)

    def test_invalid_scheme_rejected_before_proxy_resolution(self):
        req = Request("http://dashdash-tau.vercel.app/api/mac-lookup",
                      data=b"{}", method="POST")
        with patch.object(transport, "_resolve_user_proxy",
                          side_effect=AssertionError("must not resolve")):
            with self.assertRaisesRegex(URLError, "Only HTTPS"):
                transport._windows_urlopen(req, timeout=12)

    def test_read_only_requests_rejected_before_network(self):
        req = Request("https://dashdash-tau.vercel.app/api/mac-lookup")
        with patch.object(transport, "_resolve_user_proxy",
                          side_effect=AssertionError("must not resolve")):
            with self.assertRaisesRegex(URLError, "POST"):
                transport._windows_urlopen(req, timeout=12)

    def test_oversized_request_rejected_before_proxy_resolution(self):
        req = Request("https://dashdash-tau.vercel.app/api/mac-lookup",
                      data=b"x" * 40000, method="POST")
        with patch.object(transport, "_resolve_user_proxy",
                          side_effect=AssertionError("must not resolve")):
            with self.assertRaisesRegex(URLError, "oversized"):
                transport._windows_urlopen(req, timeout=12)

    def test_buffered_response_matches_urlopen_usage(self):
        with transport._Response(200, b'{"results":[]}') as reply:
            self.assertEqual(reply.status, 200)
            self.assertEqual(reply.read(3), b'{"r')
            self.assertEqual(reply.read(), b'esults":[]}')


if __name__ == "__main__":
    unittest.main()
