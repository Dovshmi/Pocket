# Pocket Extra: read-only Excel search (experimental)

Branch: experiment/extra-excel-lookup. This feature is not part of the stable v1.39.9 release.

## Usage

1. Launch the source build of the experimental branch and select **Extra**.
2. In **Excel source**, paste a workbook path or press **Browse**. You can select an approved local file or a workbook on a drive that Windows can access.
3. Search once using any value from any column. For example, `8826004` matches `88-26004`, `88 26004` and `8826004`. Customer names, IPs, VLANs, VRFs, VDOMs and other cells also work.
4. Choose any result in **Matches** to see **every nonempty column** from that Excel row, including original sheet name and physical row number.

Modern `.xlsx`, macro-enabled `.xlsm`, templates `.xltx`/`.xltm`, and legacy `.xls` are supported. `.xlsb` is not supported in this experimental build.

## Privacy and safety

- The source file is opened **read-only** and is never modified or saved by Pocket. If a rights-managed or encrypted `.xlsx` file is not a normal ZIP archive, Pocket instead reads the exact workbook **already open in desktop Excel** under the current signed-in Windows/Office account, without opening, saving or exporting the workbook.
- Pocket does not launch Excel, perform workbook recalculation, run macros or write a cache/index/database. For protected files, first open the workbook yourself in Excel and complete the normal organizational permission prompts. If Office restrictions prohibit access through automation, the lookup cannot bypass those restrictions.
- Search results, queries and chosen file path are **not persisted** to `data.json`, logs, history, backups or the repo. The chosen path is kept in memory for the current Pocket session only.
- All searching runs on the computer where Pocket is executing. Pocket makes **no HTTP/API requests** for this feature.
- Worksheets are streamed on demand so a large workbook does not need to be loaded into Pocket's result list. Only the first 120 matching rows are shown to keep the UI responsive; refine your search when there are too many results.
- Hidden worksheets are included. Column labels are inferred from the first ten rows; a column with no clear header is labeled with its Excel letter.
- `read_only=True`, `data_only=True` and `keep_links=False` are used for modern workbooks; formula cells show cached values only. If the workbook has not been recalculated and saved in Excel, a formula's cached value may be blank.
- Excel files must remain accessible through Windows file permissions; Pocket does not bypass workplace controls. Keep workplace spreadsheets and their contents off public GitHub.

## Development

Install the additional Excel readers and Windows-only `pywin32` bridge through `requirements.txt`. The standard Pocket Windows build scripts use `requirements-build.txt`, which includes these dependencies and bundles them through normal imports.

To run the focused tests:

```powershell
py -3 -m unittest tests.test_extra_excel_lookup -v
```

No sample workplace workbook, customer data or credentials are included in tests or commits.
