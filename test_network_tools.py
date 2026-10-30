"""PocketDesk TCP + vendor regression tests. Run: python -m unittest discover -v"""
from pathlib import Path
from unittest.mock import patch
import tempfile
import socket
import unittest

import network_tools as net


class NetworkTests(unittest.TestCase):
    def test_target(self):
        self.assertEqual(net.parse_target(" 192.168.0.1 "), "192.168.0.1")
        self.assertEqual(net.parse_target("::1"), "::1")
        for raw in ["", "8.8.8.0/24", "not_a_host", "192.168.0.999"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                net.parse_target(raw)

    def test_ports(self):
        self.assertEqual(net.parse_ports("443, 22 80 8000-8003, 443"), [22, 80, 443, 8000, 8001, 8002, 8003])
        for raw in ["", "0", "65536", "4-2", "abc", "1-200", "80;99999", "2--3"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                net.parse_ports(raw)

    def test_tcp_open_and_closed_localhost(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertEqual(net.check_tcp_port("127.0.0.1", port)["status"], "OPEN")
        # Some CI hosts firewall refused connections as timeouts.\n        self.assertIn(net.check_tcp_port("127.0.0.1", port)["status"], ("CLOSED", "TIMEOUT"))

    def test_normalize_mac(self):
        for raw in ("001122AABBCC", "00:11:22:AA:BB:CC", "00-11-22-aa-bb-cc", "0011.22AA.BBCC"):
            with self.subTest(raw=raw):
                self.assertEqual(net.normalize_mac(raw), "001122AABBCC")
        for raw in ["", "00:11:22:33:44", "00:11-22:33:44:55", "xyz", "00:11:22:33:44:GG", "00:11:22:33:44:55:66"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                net.normalize_mac(raw)

    def test_vendor_longest_prefix_and_special(self):
        vendors = {"001122": ["Example Large", "MA-L"],
                   "0011223": ["Example Medium", "MA-M"],
                   "001122334": ["Example Small", "MA-S"]}
        self.assertEqual(net.mac_lookup("00:11:22:33:4a:bb", vendors)["vendor"], "Example Small")
        self.assertEqual(net.mac_lookup("00:11:22:3f:ff:ff", vendors)["vendor"], "Example Medium")
        self.assertEqual(net.mac_lookup("00:11:22:ff:ff:ff", vendors)["vendor"], "Example Large")
        self.assertEqual(net.mac_lookup("02:11:22:33:44:55", vendors)["registry"], "Special")
        self.assertEqual(net.mac_lookup("01:00:5e:00:00:01", vendors)["vendor"], "Multicast / group address")
        self.assertEqual(net.mac_lookup("invalid", vendors)["vendor"], "Invalid MAC")
        self.assertEqual(net.mac_lookup("00:22:33:44:55:66", {})["vendor"], "Database not downloaded")

    def test_batch(self):
        rows = net.batch_lookup("00:11:22:33:44:55, 02-AB-CD-EE-00-01\ninvalid", {})
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[2]["vendor"], "Invalid MAC")
        with self.assertRaises(ValueError):
            net.batch_lookup("00:11:22:33:44:55 " * 5001, {})

    def test_parse_ieee_csv(self):
        sample = b'Registry,Assignment,Organization Name,Organization Address\nMA-L,001122,"A, Inc.",USA\nMA-L,012345,Example Corp,UK\n'
        result = net.parse_ieee_csv(sample, "MA-L", 6)
        self.assertEqual(result["001122"], ["A, Inc.", "MA-L"])
        with self.assertRaises(ValueError):
            net.parse_ieee_csv(b"garbage", "MA-L", 6)

    def test_import_ieee_csv_files(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "vendors.json"
            first = Path(directory) / "oui.csv"
            second = Path(directory) / "oui36.csv"
            first.write_text("Registry,Assignment,Organization Name,Organization Address\nMA-L,001122,Vendor One,EU\n", encoding="utf-8")
            second.write_text("Registry,Assignment,Organization Name,Organization Address\nMA-S,001122334,Vendor Small,EU\n", encoding="utf-8")
            self.assertEqual(net.import_ieee_csv_files([first, second], cache), 2)
            vendors, date = net.load_vendor_database(cache)
            self.assertEqual(vendors["001122334"], ["Vendor Small", "MA-S"])
            self.assertEqual(net.mac_lookup("00:11:22:33:44:55", vendors)["vendor"], "Vendor Small")
            with self.assertRaises(ValueError):
                net.import_ieee_csv_files([], cache)

    def test_ieee_http_rejection_is_explained_without_overwriting_cache(self):
        from urllib.error import HTTPError
        sample = b"existing-cache"
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "vendors.json"
            cache.write_bytes(sample)
            error = HTTPError(net.IEEE_LISTS[0][1], 418, "Blocked", None, None)
            with patch.object(net, "urlopen", side_effect=error):
                with self.assertRaisesRegex(ValueError, r"HTTP 418.*Import CSV"):
                    net.download_ieee_database(cache)
            self.assertEqual(cache.read_bytes(), sample)

    def test_ieee_gzip_and_large_registry_content(self):
        import gzip
        row = b"Registry,Assignment,Organization Name,Organization Address\nMA-L,001122,Example,US\n"
        body = gzip.compress(row)
        class Response:
            headers = {"Content-Encoding": "gzip"}
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, limit): return body
        with tempfile.TemporaryDirectory() as d, patch.object(net, "urlopen", return_value=Response()):
            with patch.object(net, "IEEE_LISTS", [net.IEEE_LISTS[0]]):
                self.assertEqual(net.download_ieee_database(Path(d) / "vendors.json"), 1)

    def test_full_download_uses_ieee_only_and_stores_cache(self):
        contents = {
            "MA-L": b"Registry,Assignment,Organization Name,Organization Address\nMA-L,001122,Large,US\n",
            "MA-M": b"Registry,Assignment,Organization Name,Organization Address\nMA-M,0011223,Medium,US\n",
            "MA-S": b"Registry,Assignment,Organization Name,Organization Address\nMA-S,001122334,Small,US\n",
            "IAB": b"Registry,Assignment,Organization Name,Organization Address\nIAB,0050C2000,Legacy,US\n",
        }
        class Response:
            def __init__(self, body): self.body = body
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, amount): return self.body
        def get(request, timeout):
            return Response(contents[next(registry for registry, url, _ in net.IEEE_LISTS if url == request.full_url)])
        with tempfile.TemporaryDirectory() as d, patch.object(net, "urlopen", side_effect=get):
            path = Path(d) / "vendors.json"
            count = net.download_ieee_database(path)
            vendors, date = net.load_vendor_database(path)
            self.assertEqual(count, 4)
            self.assertEqual(vendors["001122334"], ["Small", "MA-S"])
            self.assertNotEqual(date, "Not downloaded")
            csvfile = Path(d) / "mac.csv"
            net.export_csv(csvfile, ["mac", "vendor"], [{"mac": "00:11:22:33:44:55", "vendor": "A, Co"}])
            self.assertIn('"A, Co"', csvfile.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
