"""Remote MAC OUI client tests: mocked HTTP; no live API calls."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from pocket import dashdash_mac as mac


class Reply:
    status = 200

    def __init__(self, payload):
        self.data = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, amount):
        return self.data.read(amount)


class DashDashMacTests(unittest.TestCase):
    def test_parse_and_deduplicate(self):
        self.assertEqual(
            mac.parse_remote_macs("0011.2233.4455, 00:11:22:33:44:55\nAA-BB-CC-DD-EE-FF"),
            ["00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF"],
        )

    def test_reject_invalid_and_oversized_input_before_connecting(self):
        for raw in ("", "hello", "00:11:22", "00:11:22:33:44:GG",
                    "001122334455 00:11:22:33:44:5G",
                    "00:11:22:33:44:55\n" * 101):
            with self.subTest(value=raw[:40]), self.assertRaises(ValueError):
                mac.parse_remote_macs(raw)

    def test_posts_one_https_request_and_reorders_validated_results(self):
        def request_handler(request, timeout):
            self.assertEqual(request.full_url, mac.DASHDASH_MAC_URL)
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(timeout, mac.REQUEST_TIMEOUT)
            self.assertEqual(json.loads(request.data), {"macs": [
                "00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF"]})
            return Reply({"results": [
                {"input": "AA:BB:CC:DD:EE:FF", "mac": "AA:BB:CC:DD:EE:FF",
                 "vendor": "Second", "registry": "MA-M"},
                {"input": "00:11:22:33:44:55", "mac": "00:11:22:33:44:55",
                 "vendor": "First", "registry": "MA-L"},
            ]})
        with patch.object(mac, "urlopen", side_effect=request_handler):
            rows = mac.lookup_remote_macs(["00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF"])
        self.assertEqual([r["vendor"] for r in rows], ["First", "Second"])
        self.assertEqual([r["registry"] for r in rows], ["MA-L", "MA-M"])

    def test_reject_bad_server_data(self):
        request = ["00:11:22:33:44:55"]
        bad_payloads = [
            {"results": []},
            {"results": [{"mac": "00:11:22:33:44:55", "vendor": "", "registry": "MA-L"}]},
            {"results": [{"mac": "00:11:22:33:44:56", "vendor": "Other", "registry": "MA-L"}]},
            {"results": [{"mac": "garbage", "vendor": "Other", "registry": "MA-L"}]},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload), patch.object(
                mac, "urlopen", return_value=Reply(payload)
            ), self.assertRaises(ValueError):
                mac.lookup_remote_macs(request)

    def test_http_failures_produce_clear_errors(self):
        with patch.object(mac, "urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(ValueError, "Cannot reach DashDash"):
                mac.lookup_remote_macs(["00:11:22:33:44:55"])
        error = HTTPError(mac.DASHDASH_MAC_URL, 400, "Bad Request", {}, io.BytesIO(b""))
        with patch.object(mac, "urlopen", side_effect=error):
            with self.assertRaisesRegex(ValueError, "HTTP 400"):
                mac.lookup_remote_macs(["00:11:22:33:44:55"])

    def test_invalid_request_does_not_make_http_request(self):
        with patch.object(mac, "urlopen", side_effect=AssertionError("unexpected HTTP")):
            with self.assertRaises(ValueError):
                mac.lookup_remote_macs([])


if __name__ == "__main__":
    unittest.main()
