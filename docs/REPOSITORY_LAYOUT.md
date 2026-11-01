# Pocket repository layout and maintenance

This layout was introduced on `chore/repository-cleanup-v131`. It organizes files without changing the app's public features or the published v1.31.0 Windows download.

## Top-level files

| Path | Purpose |
| --- | --- |
| `app.pyw` | GUI entry point: windows, modes, tray integration and tool dispatch |
| `pocket/` | Importable package of 27 runtime modules plus `__init__.py` |
| `tests/test_*.py` | 34 maintained unit regression suites |
| `tests/integration/smoke_dashboard_integration.py` | Maintained real Tk GUI integration smoke (Windows/Xvfb) |
| `tests/manual/` | 16 historical manual GUI smoke scripts; not CI's release gate |
| `commands/example_commands.json` | Approved, sanitized public reference seed for new installations |
| `commands/sample_commands.json`, `public_additions.json`, `machine_catalog.json` | Public catalogue samples and test fixtures |
| `assets/` | Application icon assets |
| `docs/images/legacy/` | Historical preview images, formerly in repository root |
| `docs/archive/release-workflows/` | Old GitHub Actions release YAML, **not active workflows** |
| `docs/archive/legacy-notes/` | Outdated release candidate and development notes |
| `.github/workflows/mini-checks.yml` | Maintained Windows/Linux unit, GUI and packaging checks |
| `.github/workflows/release-v1.31.0.yml` | Existing v1.31.0 build/release recipe (not an automatic new version) |
| `build-portable.bat`, `package_portable.py` | Safe portable packaging |
| `build-exe.bat` | Local EXE packaging, now bundling **only public example data** |

Modules intentionally retain their existing filenames inside `pocket/` so feature history, import identifiers, and debugging remain recognizable. Python entry-point scripts stay in the root, not inside the import package.

## Development commands

Run from the repository root:

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 tests/integration/smoke_dashboard_integration.py --preview
```

The maintained GUI smoke requires a display: Windows directly or Xvfb on Linux. It uses a temporary application profile and public example commands. The `--preview` argument is accepted by Pocket itself; the integration test is already designed to use preview mode, so the argument above is optional.

Build on Windows, in a suitable development environment:

```bat
build-portable.bat
```

The PyInstaller build creates a self-contained portable ZIP with the approved public command seed. For standalone public EXE builds, use `build-exe.bat` or the gated release workflow.

## Private data and command libraries

Older revisions of this repository contained **two identical copies** of a 573-command workbook-derived `commands.json`, in `commands/` and `Pocket_Commands_One_Library/`. Earlier installation instructions explicitly identified that workbook as **private**.

The cleanup **untracks both copies from the current tree** and adds ignore rules to prevent accidental recommits. It does **not erase earlier Git history or cached clones**. Historical disclosure cannot be reversed just by deleting a tracked file. Rewriting public Git history would require separate approval and coordination with existing clones, forks, and releases.

The app's source installation now seeds a writable `commands.json` from `commands/example_commands.json` when no personal library exists. Existing installations with their own `commands.json` keep using it; user command data and backups are never migrated into Git. Normal, Mini, Dashboard, and Extra Mini remain offline-first.

Never commit `data.json`, personal command libraries, `vendors.json`, exported notes, credentials, or real customer/network information. Before publishing a release, inspect the generated ZIP and standalone EXE for private inputs.

## CI and archived resources

The root has only active entry points, current dependencies and build scripts. Unit tests and old GUI scripts are no longer mixed with runtime sources. Historical release YAML is stored under `docs/archive/`; GitHub Actions ignores those files. If a future version is released, add or replace a **new** gated workflow rather than reactivating an older workflow with stale asset names.

The original test coverage and existing runtime behavior were kept, including Mini note-arrow controls, native RTL Notes editing, Smart Templates, and portable AppData isolation. Full Windows and Linux regression suites and packaged-EXE checks are required before the cleanup branch is merged.
