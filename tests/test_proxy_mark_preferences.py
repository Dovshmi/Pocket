"""Workplace/direct networking and keyboard selection regression tests.

All network calls and keyboard events are mocked. These tests never send
keystrokes to a real user window or contact the internet.
"""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import runpy
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.request import Request

from pocket import dashdash_mac, dashdash_ports, hotkey_settings as hk
from pocket import ieee_https, marked_layout, network_tools
from pocket import windows_proxy_urlopen as transport
from pocket import keyboard_layout

appmod = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                        run_name="proxy_mark_tests")


class PreferenceTests(unittest.TestCase):
    def test_default_proxy_on_and_clipboard_mode(self):
        defaults = appmod["default_data"]()["settings"]
        self.assertIs(defaults["use_windows_proxy"], True)
        self.assertEqual(defaults["convert_mode"], "clipboard")
        normalized = appmod["normalize_settings"]({})
        self.assertIs(normalized["use_windows_proxy"], True)
        self.assertEqual(normalized["convert_mode"], "clipboard")
        self.assertIs(appmod["normalize_settings"]({"use_windows_proxy": False})
                      ["use_windows_proxy"], False)
        for invalid in (None, 42, "MARK", True, {}):
            self.assertEqual(appmod["normalize_settings"](
                {"convert_mode": invalid})["convert_mode"], "clipboard")
        self.assertEqual(appmod["normalize_settings"](
            {"convert_mode": "mark"})["convert_mode"], "mark")

    def test_settings_persist_without_performing_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            data = appmod["default_data"]()
            data["settings"].update(use_windows_proxy=False, convert_mode="mark")
            appmod["save_data"](path, data)
            reloaded = appmod["load_data"](path)
            self.assertFalse(reloaded["settings"]["use_windows_proxy"])
            self.assertEqual(reloaded["settings"]["convert_mode"], "mark")

    def test_ui_callbacks_modify_only_preferences(self):
        saves = []
        app = SimpleNamespace(
            settings={"use_windows_proxy": True, "convert_mode": "clipboard"},
            schedule_save=lambda: saves.append(True))
        appmod["PocketDesk"]._set_windows_proxy(app, False)
        appmod["PocketDesk"]._set_convert_mode(app, "mark")
        appmod["PocketDesk"]._set_convert_mode(app, "unknown")
        self.assertEqual(app.settings, {"use_windows_proxy": False,
                                         "convert_mode": "mark"})
        self.assertEqual(len(saves), 2)

    def test_new_shortcut_and_former_factory_shortcut_migration(self):
        self.assertEqual(hk.hotkey_label(hk.DEFAULT_CONVERT_HOTKEY),
                         "Ctrl+Alt+V")
        old = {"ctrl": True, "shift": False, "alt": True,
               "win": False, "key": "F9"}
        self.assertEqual(hk.normalize_convert_hotkey(old)["key"], "V")
        custom = dict(old, key="J")
        self.assertEqual(hk.normalize_convert_hotkey(custom), custom)
        self.assertTrue(hk.collides(
            hk.DEFAULT_CONVERT_HOTKEY, hk.DEFAULT_CONVERT_HOTKEY))


class NetworkRoutingTests(unittest.TestCase):
    def test_direct_transport_disables_proxy_configuration(self):
        with patch("urllib.request.build_opener") as build:
            build.return_value.open.return_value = "ok"
            request = Request("https://example.org/")
            self.assertEqual(transport.direct_urlopen(request, timeout=5), "ok")
            handler = build.call_args.args[0]
            self.assertEqual(handler.proxies, {})
            build.return_value.open.assert_called_once_with(request, timeout=5)

    def test_dashdash_clients_choose_correct_transport(self):
        for module, action, payload in (
            (dashdash_mac, lambda: dashdash_mac.lookup_remote_macs(
                ["00:11:22:33:44:55"], use_windows_proxy=False),
             "Cannot reach DashDash via direct HTTPS"),
            (dashdash_ports, lambda: dashdash_ports.check_remote_ports(
                "1.1.1.1", [443], use_windows_proxy=False),
             "Could not contact DashDash via direct HTTPS")
        ):
            with self.subTest(module=module.__name__), \
                 patch.object(module, "urlopen") as proxy, \
                 patch.object(module, "direct_urlopen",
                              side_effect=URLError("offline")) as direct:
                with self.assertRaisesRegex(ValueError, payload):
                    action()
                proxy.assert_not_called()
                direct.assert_called_once()

    def test_proxy_enabled_retains_existing_dashdash_post_transport(self):
        for module, action in (
            (dashdash_mac, lambda: dashdash_mac.lookup_remote_macs(
                ["00:11:22:33:44:55"], use_windows_proxy=True)),
            (dashdash_ports, lambda: dashdash_ports.check_remote_ports(
                "1.1.1.1", [443], use_windows_proxy=True))
        ):
            with self.subTest(module=module.__name__), \
                 patch.object(module, "urlopen",
                              side_effect=URLError("PAC unavailable")) as proxy, \
                 patch.object(module, "direct_urlopen") as direct:
                with self.assertRaises(ValueError):
                    action()
                self.assertEqual(proxy.call_count, 1)
                direct.assert_not_called()

    def test_ieee_get_accepts_only_official_https_registry_urls(self):
        allowed = "https://standards-oui.ieee.org/oui/oui.csv"
        ieee_https._validate(Request(allowed))
        for url in ("https://example.org/oui/oui.csv",
                    "http://standards-oui.ieee.org/oui/oui.csv",
                    allowed + "?redirect=1",
                    "https://standards-oui.ieee.org/private.csv"):
            with self.subTest(url=url), self.assertRaises(URLError):
                ieee_https._validate(Request(url))
        with self.assertRaisesRegex(URLError, "official HTTPS IEEE"):
                # POST to a valid IEEE endpoint must not be sent.
            ieee_https._validate(Request(allowed, method="POST", data=b"x"))

    def test_ieee_both_modes_use_wininet_windows_trust_for_get(self):
        request = Request(network_tools.IEEE_LISTS[0][1])
        with patch.object(ieee_https.os, "name", "nt"), \
             patch.object(ieee_https, "_windows_ieee_get",
                          return_value="native") as native, \
             patch.object(ieee_https.corporate, "direct_urlopen",
                          side_effect=AssertionError("Python TLS is not used")) as direct:
            self.assertEqual(ieee_https.open_ieee(request), "native")
            native.assert_called_once_with(
                request, timeout=25, use_windows_proxy=True)
            native.reset_mock()
            self.assertEqual(
                ieee_https.open_ieee(request, use_windows_proxy=False), "native")
            native.assert_called_once_with(
                request, timeout=25, use_windows_proxy=False)
            direct.assert_not_called()

    def test_ieee_windows_direct_never_resolves_proxy_policy(self):
        request = Request(network_tools.IEEE_LISTS[0][1])
        with patch.object(ieee_https.corporate, "_resolve_user_proxy",
                          side_effect=AssertionError("PAC must not be called")) as pac, \
             patch.object(ieee_https.ctypes, "WinDLL", create=True,
                          side_effect=RuntimeError("WinINet init")), \
             self.assertRaisesRegex(RuntimeError, "WinINet init"):
            ieee_https._windows_ieee_get(
                request, timeout=25, use_windows_proxy=False)
        pac.assert_not_called()

    def test_ieee_download_transport_routed_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "vendors.json"
            for enabled in (True, False):
                with self.subTest(windows_proxy=enabled), \
                     patch.object(ieee_https, "open_ieee",
                                  side_effect=URLError("offline")) as native, \
                     patch.object(network_tools, "urlopen") as old, \
                     patch.object(transport, "direct_urlopen") as direct:
                    with self.assertRaisesRegex(ValueError, "IEEE MA-L download failed"):
                        network_tools.download_ieee_database(
                            cache, use_windows_proxy=enabled)
                    native.assert_called_once()
                    self.assertIs(native.call_args.kwargs["use_windows_proxy"], enabled)
                    old.assert_not_called()
                    direct.assert_not_called()
            self.assertFalse(cache.exists())

    def test_ieee_legacy_library_caller_retains_urllib(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "vendors.json"
            with patch.object(network_tools, "urlopen",
                              side_effect=URLError("offline")) as old, \
                 patch.object(ieee_https, "open_ieee") as native:
                with self.assertRaisesRegex(ValueError, "IEEE MA-L download failed"):
                    network_tools.download_ieee_database(cache)
                old.assert_called_once()
                native.assert_not_called()


class FakeMarkBackend:
    def __init__(self, selected="akuo"):
        self.selected = selected
        self.current = "Clipboard: confidential original"
        self.original = self.current
        self.window = 55
        self.seq = 20
        self.restores = 0
        self.pastes = []

    def foreground(self):
        return self.window

    def wait_keys_up(self):
        return True

    @contextmanager
    def preserve_clipboard(self):
        def restore():
            self.current = self.original
            self.restores += 1
        yield restore

    def sequence(self):
        return self.seq

    def send_key(self, key):
        if key == "C" and self.selected is not None:
            self.current = self.selected
            self.seq += 1
        if key == "V":
            self.pastes.append(self.current)

    def wait_for_sequence_change(self, previous):
        return self.seq != previous

    def read_text(self):
        return self.current

    def put_text(self, value):
        self.current = value
        self.seq += 1

    def pause_after_paste(self):
        pass


class MarkSelectionTests(unittest.TestCase):
    def test_replaces_selected_text_and_restores_original_clipboard(self):
        backend = FakeMarkBackend("akuo")
        result = marked_layout.convert_selection(
            keyboard_layout.convert, target_hwnd=55, backend=backend)
        self.assertTrue(result.changed)
        self.assertEqual(backend.pastes, ["שלום"])
        self.assertEqual(backend.current, backend.original)
        self.assertEqual(backend.restores, 1)

    def test_no_selected_text_never_uses_old_clipboard(self):
        backend = FakeMarkBackend(None)
        result = marked_layout.convert_selection(
            keyboard_layout.convert, target_hwnd=55, backend=backend)
        self.assertFalse(result.changed)
        self.assertEqual(backend.pastes, [])
        self.assertEqual(backend.current, backend.original)

    def test_no_conversion_does_not_paste(self):
        backend = FakeMarkBackend("1234")
        result = marked_layout.convert_selection(
            keyboard_layout.convert, target_hwnd=55, backend=backend)
        self.assertFalse(result.changed)
        self.assertEqual(backend.pastes, [])
        self.assertEqual(backend.current, backend.original)
        self.assertEqual(backend.restores, 1)

    def test_foreground_changed_before_copy_does_not_copy(self):
        backend = FakeMarkBackend()
        backend.window = 99
        with self.assertRaisesRegex(marked_layout.MarkError, "no longer active"):
            marked_layout.convert_selection(
                keyboard_layout.convert, target_hwnd=55, backend=backend)
        self.assertEqual(backend.pastes, [])

    def test_foreground_changed_after_copy_never_pastes(self):
        class Switched(FakeMarkBackend):
            def send_key(self, key):
                super().send_key(key)
                if key == "C":
                    self.window = 777
        backend = Switched()
        result = marked_layout.convert_selection(
            keyboard_layout.convert, target_hwnd=55, backend=backend)
        self.assertFalse(result.changed)
        self.assertEqual(backend.pastes, [])
        self.assertEqual(backend.current, backend.original)


if __name__ == "__main__":
    unittest.main()
