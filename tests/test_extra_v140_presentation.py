"""Pocket 1.40 Extra: compact, lossless selected-row model tests."""
from __future__ import annotations

from pathlib import Path
import unittest

from pocket.extra_excel_lookup import ExcelHit
from pocket.extra_excel_presentation import row_overview
from pocket import app_info, extra_excel_ui


def hit(sheet="FG-26-METRO1"):
    return ExcelHit(
        sheet=sheet, row=370,
        fields=(
            ("לקוח (A)", "קופיקס מצלמות"),
            ("קוד קישור (B)", "82-8703275"),
            ("מס' הזמנה (C)", "89597620"),
            ("קוד קבוצה א (D)", "88-29673"),
            ("VRF (F)", "cofix-cam"),
            ("VDOM (G)", "cofix-cam"),
            ("zone (H)", "isp"),
            ("IP address (I)", "147.236.124.122"),
            ("VLAN FG (J)", "367"),
            ("pe/מבואה (K)", "82-9356371 vlan 513"),
        ),
        matched_columns=("VRF (F)",), exact=True)


class ExtraPresentationTests(unittest.TestCase):
    def test_compact_model_shows_expected_customer_circuit_and_ip(self):
        overview = row_overview(hit())
        self.assertEqual(overview.sheet, "FG-26-METRO1")
        self.assertEqual(overview.row, 370)
        self.assertEqual(overview.customer.value, "קופיקס מצלמות")
        values = {cell.label: cell.value for pair in overview.pairs for cell in pair}
        self.assertEqual(values["קוד קישור"], "82-8703275")
        self.assertEqual(values["קוד קבוצה"], "88-29673")
        self.assertEqual(values["VRF"], "cofix-cam")
        self.assertEqual(values["VDOM"], "cofix-cam")
        self.assertEqual(values["FortiGate IP"], "10.238.2.26")
        self.assertEqual(values["VLAN FG"], "367")

    def test_remaining_columns_are_lossless_and_not_reordered(self):
        original = hit().fields
        overview = row_overview(hit())
        selected_indices = [
            overview.customer.field_index,
            *(cell.field_index for pair in overview.pairs for cell in pair)]
        seen = {index for index in selected_indices if index is not None}
        self.assertEqual(len(seen), 6)
        self.assertEqual(overview.remaining, tuple(
            item for index, item in enumerate(original) if index not in seen))
        self.assertIn(("IP address (I)", "147.236.124.122"), overview.remaining)
        self.assertIn(("מס' הזמנה (C)", "89597620"), overview.remaining)

    def test_bad_sheet_never_fabricates_fortigate_and_other_fields_remain(self):
        overview = row_overview(hit("Netscreen-2"))
        ip = next(cell.value for pair in overview.pairs
                  for cell in pair if cell.label == "FortiGate IP")
        self.assertEqual(ip, "—")
        self.assertEqual(overview.customer.value, "קופיקס מצלמות")
        self.assertIn(("IP address (I)", "147.236.124.122"), overview.remaining)

    def test_missing_columns_do_not_steal_numeric_order_or_public_ip(self):
        source = ExcelHit("FG25", 24, (
            ("שם העסק (A)", "Sample Client"),
            ("קוד קבוצה (B)", "88-25673"),
            ("מספר הזמנה (C)", "98597620"),
            ("IP address (D)", "147.236.124.122"),
        ), (), False)
        overview = row_overview(source)
        values = {cell.label: cell.value for pair in overview.pairs for cell in pair}
        self.assertEqual(values["קוד קישור"], "—")
        self.assertEqual(values["FortiGate IP"], "10.238.2.25")
        self.assertEqual(values["קוד קבוצה"], "88-25673")
        self.assertEqual(overview.customer.value, "Sample Client")
        self.assertIn(("מספר הזמנה (C)", "98597620"), overview.remaining)

    def test_expansion_ui_keeps_database_search_and_soc_button_unchanged(self):
        source = Path(extra_excel_ui.__file__).read_text(encoding="utf-8")
        self.assertIn("presentation.row_overview(hit)", source)
        self.assertIn('app._extra_excel_columns_expanded', source)
        self.assertIn("Show other columns", source)
        self.assertIn('details.pack(side="left", fill="both", expand=True)', source)
        self.assertIn("Copy FortiGate IP", source)
        self.assertIn('source_name.bind("<Button-1>"', source)
        self.assertNotIn("path_field = design.entry(", source)
        self.assertNotIn('path_field.bind("<Return>"', source)
        self.assertIn('soc.make_soc_draft(hit)', source)

    def test_settings_reports_143(self):
        self.assertEqual(app_info.version_label(), "v1.43")


if __name__ == "__main__":
    unittest.main()
