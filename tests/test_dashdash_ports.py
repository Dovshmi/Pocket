"""DashDash remote TCP API checks, with no live network requests."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from pocket import dashdash_ports as remote


class Reply:
    status = 200

    def __init__(self, payload):
        self.body = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, amount):
        return self.body.read(amount)


class RemotePortTests(unittest.TestCase):
    def test_accepts_one_public_ipv4_and_sorts_unique_ports(self):
        self.assertEqual(remote.validate_remote_check(" 1.1.1.1 ", [443, 80, 80]),
                         ("1.1.1.1", [80, 443]))

    def test_rejects_non_public_addresses_and_ipv6(self):
        for ip in ("127.0.0.1", "192.168.1.1", "10.1.2.3", "172.16.4.2",
                   "169.254.0.1", "100.64.0.1", "0.0.0.0", "255.255.255.255",
                   "192.0.0.9", "192.88.99.2", "198.51.100.10", "::1",
                   "localhost", "1.1.1.0/24", "8.8.8.999"):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                remote.validate_remote_check(ip, [443])

    def test_rejects_too_many_or_invalid_ports(self):
        for ports in ([], list(range(1, 18)), [0], [65536], ["443"], [True]):
            with self.subTest(ports=ports), self.assertRaises(ValueError):
                remote.validate_remote_check("1.1.1.1", ports)

    def test_post_json_and_validate_returned_results(self):
        def fake_urlopen(request, timeout):
            self.assertEqual(request.full_url, remote.DASHDASH_PORT_CHECK_URL)
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(timeout, remote.REMOTE_TIMEOUT_SECONDS)
            payload = json.loads(request.data)
            self.assertEqual(payload, {"ip": "1.1.1.1", "ports": "80,443"})
            return Reply({"ip": "1.1.1.1", "results": [
                {"port": 443, "service": "HTTPS", "status": "OPEN", "ms": 21},
                {"port": 80, "service": "HTTP", "status": "TIMEOUT", "ms": 1200},
            ]})
        with patch.object(remote, "urlopen", side_effect=fake_urlopen):
            result = remote.check_remote_ports("1.1.1.1", [443, 80, 443])
        self.assertEqual([row["port"] for row in result], [80, 443])
        self.assertEqual([row["status"] for row in result], ["TIMEOUT", "OPEN"])

    def test_server_response_must_match_requested_ports(self):
        invalid = [
            {"ip": "8.8.8.8", "results": [{"port": 443, "status": "OPEN", "ms": 2}]},
            {"ip": "1.1.1.1", "results": []},
            {"ip": "1.1.1.1", "results": [
                {"port": 80, "status": "OPEN", "ms": 3},
                {"port": 80, "status": "OPEN", "ms": 3}]},
            {"ip": "1.1.1.1", "results": [{"port": 80, "status": "MAYBE", "ms": 2}]},
            {"ip": "1.1.1.1", "results": [{"port": 80, "status": "OPEN", "ms": "3"}]},
        ]
        for value in invalid:
            with self.subTest(value=value), patch.object(
                remote, "urlopen", return_value=Reply(value)
            ), self.assertRaises(ValueError):
                remote.check_remote_ports("1.1.1.1", [80])

    def test_http_errors_explain_failure(self):
        error = HTTPError(remote.DASHDASH_PORT_CHECK_URL, 400, "Bad request", {},
                          io.BytesIO(b'{"error":"Only public IPv4 addresses are supported"}'))
        with patch.object(remote, "urlopen", side_effect=error):
            with self.assertRaisesRegex(ValueError, "HTTP 400"):
                remote.check_remote_ports("1.1.1.1", [443])

    def test_offline_failure_is_clear(self):
        with patch.object(remote, "urlopen", side_effect=URLError("no connection")):
            with self.assertRaisesRegex(ValueError, "Could not contact DashDash"):
                remote.check_remote_ports("1.1.1.1", [443])

    def test_public_validation_does_not_connect(self):
        with patch.object(remote, "urlopen", side_effect=AssertionError("must not connect")):
            with self.assertRaises(ValueError):
                remote.check_remote_ports("192.168.1.1", [443])


if __name__ == "__main__":
    unittest.main()
