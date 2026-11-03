# Pocket Cat — experimental feature on `test-branch`

Pocket Cat is a small, **original black pixel cat** inspired by the behavior of
the classic Linux/X11 [Oneko](https://manpages.ubuntu.com/manpages/bionic/man6/oneko.6.html).
It is **not an imported sprite sheet or copy of another application's art**.
This experiment is available on `test-branch` only. It is **not included in
the published v1.32.0 stable release**.

## What it does

- Uses a detailed **original 32×32 charcoal-black pixel design** with
  layered shading, golden eyes, soft ear details and a more expressive face.
- Has **four frames per pose** for smoother walking, tail movement, blinking,
  breathing, grooming, scratching, stretching, yawning and playing.
- Wanders independently through the **unoccupied areas of the current Pocket window**.
  Uses a pathfinding grid to avoid visible buttons, labels, input fields,
  result tables, scrolling views and the native Windows note editor.
- While you type or select data in a focused entry, editor or results list,
  the cat pauses roaming and quietly sits or blinks until you finish.
- Occasionally investigates the pointer **inside Pocket only**, but only
  along a path that never crosses protected UI. Can wake up when it moves.
  It is not a desktop-wide cursor follower.
- Resizes/repositions with **Normal, Mini, Dashboard and Extra Mini**.
- Prefers quiet edges instead of walking across content. The cat is
  **click-through**, so it cannot activate buttons or steal editing focus.
- If a page does not offer enough room for its *entire* body, it **hides
  rather than covering an input, note, or result**. It reappears on a
  less crowded page. Switching tabs immediately invalidates stale paths.
- Hides when Pocket goes to the tray or a modal dialog is open.
- Has **no internet calls, file access, clipboard access, global pointer
  hooks, command execution, background thread or cloud dependency**.
- Stores only the enabled/disabled preference under
  `settings.pocket_cat` in Pocket's existing `data.json`.
  Animation state and pointer samples are ephemeral.

## Turn it on or off

Open **Settings** in any working mode. In Normal/Mini find
**Behavior & privacy → Pocket Cat companion**; in Dashboard find
**Clipboard & privacy → Pocket Cat companion**.

The experiment is **enabled by default** in `test-branch`. Untick the switch
to hide the pet immediately and stop its animation timer. The choice is saved
locally. Nothing changes in your notes, commands, shortcuts or clipboard.

The tiny **Extra Mini** launcher uses the same setting as your working layout.

## Try it from source

Requirements: **Windows 10 or 11**, Python 3.10+ and Pocket dependencies.

```powershell
git clone https://github.com/Dovshmi/Pocket.git
cd Pocket
git switch test-branch
.\install.bat
.\run.bat
```

Or launch a visible development window without using the tray:

```powershell
py -3 app.pyw --preview
```

For a standalone build, run `.\build-exe.bat`. For a full portable build,
run `.\build-portable.bat`. Alternatively, download the **test-branch preview**
artifact from a successful
[regression-checks workflow run](https://github.com/Dovshmi/Pocket/actions/workflows/mini-checks.yml).

**Note:** the branch preview is not a stable GitHub release. Pocket's
Windows binaries are unsigned; follow organizational application policies.

## Design and technical constraints

### An overlay, not a new Pocket widget

`pocket/cat_companion.py` contains:

- `pocket/cat_sprites.py`: original 32×32, four-frame sprite art with
  dynamic expressions and a palette designed for Pocket's dark themes.
- `pocket/cat_navigation.py`: `SafeSpace` collision model and
  `CatMotion` behavior engine. Routes use local widget geometry, never
  widget contents or captured user data. Both are testable without a GUI.
- `pocket/cat_companion.py`: protected-widget detection and an adaptive
  **32 / 40 / 48 pixel** transparent, no-focus overlay rendered with Tk's
  built-in `PhotoImage`.
  Win32 styles `WS_EX_TRANSPARENT`, `WS_EX_NOACTIVATE` and
  `WS_EX_TOOLWINDOW` make it click-through and keep it out of Alt-Tab.

The overlay is **not** a full-screen canvas and does **not** sit inside a
text editor, content list or toolbar. Existing controls remain native and
fully interactive. It is preserved through theme/layout rebuilds and
destroyed cleanly at shutdown.

### Fail closed

The effect is enabled **only on Windows** because the click-through contract
requires Windows APIs. If transparent hit-testing cannot be established, the
cat won't open; Pocket and all its original tools continue to work.
Linux regression tests still exercise the independent motion engine.

### Performance

- One Tk UI-thread callback approximately every **125 ms**, registered
  with Pocket's existing cancellable `TaskManager`.
- No animation callback while the companion is disabled.
- Sprites are created and cached lazily; no disk loads or network requests.
- Navigation uses already mapped widget *geometry*, updated periodically
  and immediately after tab/layout changes. No OS-wide hooks or input interception.
- The overlay is hidden when Pocket is hidden. No additional active polling
  loop is launched in a thread.

### How to validate

```powershell
py -3 -m unittest tests.test_cat_companion -v
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 tests/integration/smoke_dashboard_integration.py
```

On Windows, check that the cat animates wherever a **clear path is available**
in each of the four modes, and hides on crowded screens rather than obscuring
notes, input fields or result data. Verify that controls still work **through** its popup,
that it doesn't steal focus, and that hiding, moving, theming and exiting
Pocket never leave an orphan cat window.

### Experiment boundaries

This is a small **in-application companion**, not an app-wide desktop pet.
It does not follow the mouse outside Pocket, interact with saved records,
jump between open software windows, or change any network behavior.

The feature can be removed cleanly if the experiment doesn't fit Pocket's
minimal UI. Leave `main` on stable code until the experiment passes Windows
testing and the user chooses to merge it.
