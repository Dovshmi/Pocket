"""SOC Outlook drafting from synthetic Pocket Extra rows; no actual email sent."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from pocket.extra_excel_lookup import ExcelHit
from pocket import extra_soc_outlook as soc


def row(sheet="FG-2.8-METRO1", fields=None):
    return ExcelHit(
        sheet=sheet, row=123,
        fields=tuple(fields) if fields is not None else (
            ("לקוח (A)", "לקוח דוגמה"),
            ("קוד קישור (B)", "82-1234567"),
            ("קוד קבוצה (C)", "88-27582"),
            ("VDOM (H)", "example-vdom"),
        ), matched_columns=("קוד קבוצה (C)",), exact=True)


class SocDraftTests(unittest.TestCase):
    def test_fortigate_ip_from_sheet_names(self):
        cases = {
            "FG-2.8-METRO1": "10.238.2.8",
            "FG-2.8-IPVPN": "10.238.2.8",
            "FG25": "10.238.2.25",
            "FG-17-METRO1": "10.238.2.17",
            "FG-26": "10.238.2.26",
            "FG_15-NETS": "10.238.2.15",
            "FG Projects": "",
            "FG Cluster ID": "",
            "FG-0": "",
            "FG-255": "",
            "FG-999": "",
            "Archive FG25": "",
        }
        for sheet, expected in cases.items():
            with self.subTest(sheet=sheet):
                self.assertEqual(soc.fortigate_ip_from_sheet(sheet), expected)

    def test_selected_row_drives_subject_and_body(self):
        draft = soc.make_soc_draft(row())
        self.assertEqual(draft.details.customer, "לקוח דוגמה")
        self.assertEqual(draft.details.line_code, "82-1234567")
        self.assertEqual(draft.details.vdom, "example-vdom")
        self.assertEqual(draft.details.fortigate_ip, "10.238.2.8")
        self.assertEqual(draft.subject, "לקוח דוגמה 82-1234567 פנייה לSOC")
        for needle in ("שם העסק / הלקוח", "קוד קו", "10.238.2.8",
                       "example-vdom", "איש קשר", "מספר טלפון",
                       "תיאור התקלה / הבקשה", "מספר פנייה קודמת",
                       "באישור מומחה – שם המומחה", soc.PLACEHOLDER):
            self.assertIn(needle, draft.body)
        self.assertIn('dir="rtl"', draft.html_fragment)
        # Both Classic Outlook HTML and New Outlook mailto plain text use
        # the same field order: expert directly beneath contact person.
        for representation in (draft.body, draft.html_fragment):
            self.assertLess(representation.index("איש קשר"),
                            representation.index("באישור מומחה – שם המומחה"))
            self.assertLess(representation.index("באישור מומחה – שם המומחה"),
                            representation.index("מספר טלפון"))

    def test_customer_and_vdom_header_variants(self):
        hit = row("FG25", (
            ("שם לקוח (A)", "חברה לדוגמה"),
            ("מספר קו (B)", "828811234"),
            ("שם VDOM (E)", "customer-vdom"),
        ))
        info = soc.details_from_hit(hit)
        self.assertEqual(info.customer, "חברה לדוגמה")
        self.assertEqual(info.line_code, "828811234")
        self.assertEqual(info.vdom, "customer-vdom")
        self.assertEqual(info.fortigate_ip, "10.238.2.25")
        self.assertFalse(info.missing())

    def test_no_guess_for_missing_sheet_or_line_code(self):
        hit = row("FG Projects", (
            ("שם לקוח (A)", "Test Customer"),
            ("קוד קבוצה (C)", "88-27582"),
            ("מספר לקוח (D)", "999999"),
            ("VRF (G)", "test-vrf"),
        ))
        draft = soc.make_soc_draft(hit)
        self.assertEqual(draft.details.customer, "Test Customer")
        self.assertEqual(draft.details.line_code, "")
        self.assertEqual(draft.details.fortigate_ip, "")
        self.assertEqual(draft.details.vdom, "")
        self.assertEqual(set(draft.details.missing()),
                         {"קוד קו", "IP FortiGate", "VDOM"})
        self.assertIn(soc.PLACEHOLDER, draft.subject)
        self.assertNotIn("88-27582", draft.subject)
        self.assertNotIn("999999", draft.subject)

    def test_cell_contents_escaped_and_subject_single_line(self):
        hit = row("FG-17-METRO1", (
            ("שם העסק (A)", "<script>alert(1)</script>\r\nFake subject"),
            ("קוד קו (B)", "82-1234\nbcc: invalid"),
            ("VDOM (E)", "<test&vdom>"),
        ))
        draft = soc.make_soc_draft(hit)
        self.assertNotIn("\r", draft.subject)
        self.assertNotIn("\n", draft.subject)
        self.assertNotIn("<script>", draft.html_fragment)
        self.assertIn("&lt;script&gt;", draft.html_fragment)
        self.assertIn("&lt;test&amp;vdom&gt;", draft.html_fragment)

    def test_existing_outlook_signature_is_preserved(self):
        markup = '<html><head></head><body class="outlook"><p>Signature</p></body></html>'
        inserted = soc._insert_before_signature("<p>SOC INFO</p>", markup)
        self.assertIn('<body class="outlook"><p>SOC INFO</p>', inserted)
        self.assertIn("<p>Signature</p>", inserted)
        self.assertLess(inserted.index("SOC INFO"), inserted.index("Signature"))

    def test_classic_outlook_opens_unsent_com_draft(self):
        actions = []

        class FakeMail:
            HTMLBody = ""
            Subject = ""
            def Display(self):
                actions.append("display")
                self.HTMLBody = "<html><body><p>Corporate signature</p></body></html>"
            def Send(self):
                raise AssertionError("Pocket must NEVER send a SOC email")
            def Save(self):
                raise AssertionError("Pocket must not save SOC email")

        mail = FakeMail()
        fake_client = types.ModuleType("win32com.client")
        fake_client.Dispatch = lambda app: FakeOutlook() if app == "Outlook.Application" else None
        class FakeOutlook:
            def CreateItem(self, item):
                self_test = self
                actions.append(("create", item))
                return mail

        fake_win32com = types.ModuleType("win32com")
        fake_win32com.__path__ = []
        fake_win32com.client = fake_client
        draft = soc.make_soc_draft(row())
        with patch.dict(sys.modules, {
            "win32com": fake_win32com,
            "win32com.client": fake_client,
        }), patch.object(soc.sys, "platform", "win32"):
            result = soc.open_draft(draft)
        self.assertEqual(result, "outlook")
        self.assertEqual(actions, [("create", 0), "display"])
        self.assertEqual(mail.Subject, draft.subject)
        self.assertIn("SOC", mail.HTMLBody)
        self.assertIn("Corporate signature", mail.HTMLBody)
        self.assertNotIn("mailto", mail.HTMLBody)

    def test_new_outlook_falls_back_to_windows_default_mailto(self):
        links = []
        draft = soc.make_soc_draft(row())
        fake_client = types.ModuleType("win32com.client")
        def fail_dispatch(_name):
            raise RuntimeError("Classic Outlook COM not available")
        fake_client.Dispatch = fail_dispatch
        fake_win32com = types.ModuleType("win32com")
        fake_win32com.__path__ = []
        fake_win32com.client = fake_client
        with patch.dict(sys.modules, {
            "win32com": fake_win32com,
            "win32com.client": fake_client,
        }), patch.object(soc.sys, "platform", "win32"), \
                patch.object(soc.os, "startfile", create=True,
                             side_effect=links.append):
            result = soc.open_draft(draft)
        self.assertEqual(result, "default_mail")
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].startswith("mailto:?subject="))
        self.assertIn("&body=", links[0])
        self.assertNotIn("bcc=", links[0])


if __name__ == "__main__":
    unittest.main()
