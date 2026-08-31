# KittyEcosystem v1
### Course of Temptation mod toolchain -- C# edition

KittyEcosystem v1 is a full C# rewrite of the KittyPatcher toolchain. Every tool -- patcher, validator, diff assistant, scaffold generator, mod converter, port pipeline, test runner, and GUI launcher -- has been rebuilt in C# as a self-contained native executable. No Python interpreter, no pip installs, no runtime dependencies. Download, extract, run.

---

## Contents of this folder

```
KittyEcosystem.v1/
    KittyEcosystem_Window.v1.zip    <- Windows 10 / 11 (64-bit)
    KittyEcosystem_Linux.v1.zip     <- Linux (x64)
    KittyEcosystem_Mac.v1.zip       <- macOS (Apple Silicon and Intel)
    kittypatcher_complexity.html    <- version-by-version complexity table
    README_for_Ecosystem.md         <- this file
```

Extract the zip that matches your operating system. Each zip is self-contained -- you do not need the others. `kittypatcher_complexity.html` is shared across all platforms and lives here at the top level; open it in any browser.

---

## Why C#

The original toolchain was written in Python. Python made iteration fast but came with real costs that grew as the ecosystem grew.

**Startup and execution speed.** The Python patcher on a large mod set (80+ mods, 22 MB HTML) took several minutes per patch run before the cache was added. The C# version processes the same workload in a fraction of that time due to compiled execution and more efficient string handling. The patch cache is still present and still gives near-instant results on cache hits, but the underlying patch phase itself is substantially faster even on a cold run.

**Time complexity.** Both versions share the same algorithmic structure -- the patching pipeline is O(M x D) where M is the number of mods and D is the number of directives per mod. What changes is the constant factor. C# compiled code runs without interpreter overhead, without GIL contention on parallel string operations, and without the repeated bytecode dispatch that Python pays on every operation. For a workload that is fundamentally string-intensive (scanning a 22 MB HTML file hundreds of times per run), that constant factor matters significantly.

**Space complexity.** The Python version held multiple copies of the HTML in memory simultaneously during the patch phase -- one for reading, one being built, one per partial replace pass. The C# version uses a single in-place `StringBuilder` buffer with targeted mutation, keeping peak memory usage at roughly 2x the HTML size versus Python's 4-5x across a full patch run.

**Zero-dependency distribution.** The Python executables built with PyInstaller bundled the entire CPython interpreter and all dependencies into each binary. The C# executables are self-contained .NET builds with no bundled interpreter and no pip dependency chain. Users no longer need to worry about Python version mismatches, missing packages, or BeautifulSoup compatibility issues.

**Cross-platform native binaries.** The C# build produces genuine native executables for Windows, Linux, and macOS from the same codebase. Each platform zip is compiled for that target -- not a compatibility shim. Linux and macOS users get binaries that behave like first-class native tools.

A full operation-by-operation breakdown of time and space complexity across every version from v0.5.3 to v0.7.6 (C#) is in `kittypatcher_complexity.html`. It covers every phase of the patch pipeline -- extraction, inner replacement sweep, registry injection, batch pre-pass, cache -- with per-version columns showing where complexity improved, where it stayed the same, and what the C# port changes at the constant-factor level.

---

## KittyPatcher v0.7.6

KittyPatcher applies `.mod` files to your game HTML before you play. Drop your mods in the `mods/` folder, run the patcher, and the patched game opens in your browser. The original HTML is never modified.

No `.mod` file changes are required when upgrading from v0.7.4 or v0.7.5. All existing mods are fully compatible.

---

## Changelog

### v0.7.6 (+60 lines)

**BUG FIX: Replace: and `~~` blocks now apply in full load order, including duplicate anchors across mods.**

`mod_dict` was a plain Python dict (`str -> (new, guards)`). During the sequential merge phase, `dict.update()` silently overwrote earlier entries whenever two mods had the same OLD anchor string. The last mod to merge won and all prior mods' replacements for that anchor were permanently lost before any HTML was touched.

Real-world impact: Bits & Fun v1.3.3f lost 199 of its `~~` replacement blocks whenever other mods happened to target the same vanilla text. 97 were overwritten by mods with identical With: bodies (correct by accident). 102 were overwritten by mods with different bodies, meaning B&F's changes were never applied at all. No error, no log entry, just silently missing content. Anyone running B&F alongside CM mods was affected.

Fix: added `mod_list` alongside `mod_dict`. `mod_list` is an ordered list of `(old_key, source_mod)` tuples that records every insertion including duplicates. Phase 1 now iterates `mod_list` in insertion order and looks up each entry in `mod_dict` for the With: body. When the same OLD anchor appears multiple times, each entry applies in sequence against the live HTML so later mods see the HTML as modified by earlier ones. `mod_dict` is retained for inner-replacement (same-mod nesting) lookups which have no cross-mod ordering concern. An `ORDERING WARNING` is emitted in the log whenever duplicate OLD anchors are detected across mods.

---

### v0.7.5 (+46 lines)

**BUG FIX (critical): Struct directive body termination was swallowing subsequent directives into the JS script block.**

`Insert Into Object`, `Append Array`, `Insert Into Array`, `Append Variable to Class`, `Append Function to Class`, and `Merge Into Object` used a private terminator loop that only checked other struct-kind tokens (`_STRUCT_KINDS`). Any non-struct directive appearing immediately after a struct directive body was silently absorbed into that body and injected verbatim into the JS script block.

Real-world impact: `CM_BC.v2.mod` has an `Insert Into Object [setup.miscitems]:` immediately followed by `Append To Passage [CMBCCreampieAftermath]:`. The entire Append To Passage directive header and body were injected into `setup.miscitems` as raw JS content. The JS parser hit `To` as an unexpected identifier and aborted the entire `<script>` block, cascading into every `setup.*` function appearing as undefined and breaking all CM mods simultaneously.

Fix: replaced the private terminator loop with `_find_next_directive`, which checks all 35 directive token types uniformly.

**BUG FIX (critical): Insert After/Before was missing script-block context detection.**

The batch Insert After path (added in v0.7.3) and the non-batch Insert After/Before path were both missing the `IsInsideScriptBlock` check that the C# patcher has always had. When an anchor matched inside the `<script>` block, passage-markup bodies containing `<<set $foo to bar>>` were injected raw into JavaScript, producing `SyntaxError: Unexpected identifier 'To'` and aborting the script block entirely. This is the same cascade failure as above but triggered by a different path.

Fix: added `_is_in_script_block(html, pos)` helper (direct port of C# `PatchEngine.IsInsideScriptBlock`) and applied it at all three injection sites. Bodies in passage context now go through `escape_twine_tags()` so `<<macros>>` are stored as HTML entities; bodies in script context stay raw JS.

**FEATURE: `pid="auto"` and `position="auto"` now work in legacy `~~` delimiter blocks.**

`_resolve_pid_auto_in_anchor` only handled the raw `pid="auto"` form. When `EscapeTwineTags()` encoded the quotes to `&quot;auto&quot;` on legacy `~~` anchor keys, the pid retry block in `patch_html_file` (which checks for the raw form) never fired, and `position="auto"` was never resolved in anchors at all.

Fix: extended the function to handle both raw and HTML-encoded forms for both `pid` and `position`. Called immediately after `_normalize_anchor` for both `old_lines` and `_old_lines_raw` so `~~` delimiter blocks and new-style Replace: directives behave identically.

**BUG FIX: `[Mod]` section header lines were not stripped before `proc_replacement_old`.**

Mods using the DoggyPatcher-compatible `[Mod]...key:value` header format (without `#` prefixes) had those lines pass through the header-strip loop unchanged, since it only stripped `#`-prefixed lines. The `[Mod]` and bare key:value lines then entered the `~~/~` splitter as content, making the entire header block the Replace: anchor and producing spurious "No match found" failures that attributed the whole mod as failed.

Fix: the header-strip loop now tracks `[Mod]..[/Mod]` section state and skips bare key:value lines inside it.

---

### v0.7.4 (+201 lines)

**BUG FIX: `[Mod]` section header not stripped before `proc_replacement_old`.**

Same class of bug as fixed again in v0.7.5. Initial fix in v0.7.4 for `proc_replacement_old`; the v0.7.5 fix extended coverage.

**BUG FIX (critical): Struct directive body termination (first discovery).**

First occurrence of the struct body termination bug described above. v0.7.4 identified the issue; v0.7.5 completed the fix for all affected struct directive types.

**BUG FIX (critical): Insert After/Before script-block context detection (first discovery).**

First occurrence of the script-block injection context bug described above. v0.7.4 identified the issue; v0.7.5 ported the full `IsInsideScriptBlock` fix from C#.

**BUG FIX: Replace: anchor encoding for script-block targets.**

`_normalize_anchor` calls `escape_twine_tags()` which encodes raw quotes to `&quot;` before searching. Correct for passage content (HTML-encoded in `tw-passagedata` blocks) but wrong for script block content which stores raw characters. Replace: anchors targeting JS object entries (e.g. `setup.storyhints.db` entries, `setup.inclinations`) were silently failing with "No match found" because `&quot;key&quot;` never matches `"key"` in the script block.

Fix: two-pass search -- encoded anchor first (passage targets), raw anchor fallback when the encoded search misses and the anchor contains no passage tag (script-block indicator). Log message distinguishes fallback hits.

**NEW: Hook parameter destructuring injection.**

The Hook wrapper function signature is now always `function()` regardless of the original function's parameter list. When the original function has named parameters, the patcher injects `const [p1, p2, ...] = arguments;` at the top of the wrapper body. This makes all original parameter names available by name inside every hook body without requiring `arguments[N]` indexing. Default values and rest spread prefixes are stripped from param names before injection so the destructuring assignment is always valid JS.

**NEW: Hook local-variable static analysis warning.**

When building a Hook wrapper, the patcher now scans the original function body for `let`/`const`/`var` declarations and checks whether the hook body references any of those names as whole-word identifiers. If any match is found, a `HOOK WARNING` is written to alllogs identifying the out-of-scope locals by name. These names are inaccessible in the hook wrapper and cause a `ReferenceError` at runtime. Parameter names (injected via destructuring) are excluded from the warning.

---

### v0.7.3 (+389 lines)

**NEW: Content-addressed SHA-256 patch cache.**

Cache key is SHA-256 of the vanilla HTML + all mod file contents in sorted load order. On a cache hit the full load and patch phases are skipped and the cached patched HTML is served directly (~4 min to ~0.2s). Cache is stored in `mods/logs/cache/`, pruned to 10 entries. Disable via `[cache] enabled = false` in `kitty_config.toml`.

**SPEEDUP: Append To Passage and Insert After/Before batch pre-pass.**

207 Append To Passage calls across 82 mods previously caused 207 separate O(22MB) regex scans of the full HTML. v0.7.3 collects all appends and inserts targeting the same passage or anchor, then applies them in a single right-to-left pass per unique target. The number of full-HTML scans drops from one per directive to one per unique target. Injection order is preserved; guards are evaluated per-entry at apply time, not at collection time.

**BUG FIX: Cache not written when patch has failures.**

`patch_html_file` now returns `(replacements_made, replacements_failed, failed_mods)`. Cache is only written on clean runs with zero failures. A run with any failed directive always produces a fresh patch on the next run.

**BUG FIX: Hook conflict handling.**

When multiple mods Hook the same function, the second and later hook bodies were silently dropped. v0.7.3 appends each additional hook body into the existing wrapper so all mods fire in load order. The original function is called once.

**BUG FIX: Cache key included log files.**

`_compute_cache_key` now explicitly excludes the `logs/` subdirectory from the hash walk. Log file changes (including simply opening a log in a text editor) no longer cause spurious cache misses.

---

### v0.7.2 (+334 lines)

**SPEEDUP: `_split_html` passage dictionary and metadata index.**

At the start of `patch_html_file`, the HTML is parsed once into `passage_dict` (name -> body string, O(1) lookup) and `passage_meta` (name -> open tag + absolute start/end positions). All passage-scoped directives (`Replace In Passage`, `Append/Prepend To Passage`, `Add Tag To Passage`, `Clone Passage`, `Wrap Passage`, `Replace In All Passages`, `Add StoryVar`) now do O(1) dict lookups instead of O(H) regex scans over the full 22MB HTML. After Phase 4 mutations, `_reassemble_html` writes only changed passage bodies back into the string using right-to-left splicing so earlier offsets stay valid.

**SPEEDUP: `_fast_search` literal pre-pass for Replace: anchors.**

Before falling back to a compiled regex, `_fast_search` tries `str.find()` on the literal form of the anchor. `str.find()` is roughly 100x faster than a compiled regex on a 16MB string with no backtracking. Only reaches regex if the literal search misses.

**SPEEDUP: Script block extracted and cached once.**

`_split_html` extracts all `<script>` blocks and concatenates them into a single `script_block` string (~0.1MB). `IfFunctionExists` guards and `Add Function` duplicate checks search this string instead of the full 22MB HTML. `_script_block` is refreshed after Phase 4 (Add Javascript injections) before Phase 7 guard checks, so functions defined via `Add Javascript` rather than `Add Function` are visible to guards.

**SPEEDUP: Guard evaluation uses passage_dict and passage_meta.**

`_check_guards` accepts `passage_dict`, `passage_meta`, and `script_block` parameters. `IfPassageExists`, `IfPassageNotExists`, `IfPassageContains`, and `IfPassageHasTag` guards now do O(1) dict lookups and open-tag string checks instead of O(H) regex scans over the full HTML.

**SPEEDUP: Log buffering.**

`handle_output` now accumulates log lines in memory (`_log_buffer`) instead of opening and closing the log file on every call. `flush_logs()` is called at phase boundaries and at the end of `patch_html_file`. Eliminates hundreds of file open/close syscalls per patch run.

**SPEEDUP: PID collision detection uses `passage_meta`.**

`_detect_pid_collisions` extracts existing PIDs from `passage_meta` open tags (already parsed) instead of running `re.finditer` over the full HTML.

**BUG FIX: `alllogs` now writes to both MainPatchLog and ModPatchLog.**

Previously `alllogs` wrote only to MainPatchLog. Fixed to write to both.

---

### v0.7.1 (+features from v0.7.0 base)

**NEW: `Merge Into Object [name]:`** -- deep-merges a JSON/object literal into an existing nested JS object at every level instead of a top-level append.

**NEW: `Clone Passage [Src] As [Dst]:`** -- copies an existing passage body and tags under a new name. Registered in the passage registry immediately so Phase 4 directives can target the clone.

**NEW: `Wrap Passage [name]: before: | after:`** -- like Hook but for passage bodies. Injects content at the start or end of a named passage body.

**NEW: `Replace In All Passages [tag]:`** -- applies a Replace:/With: replacement across every passage carrying a named tag. Processes all matching passages in a single directive.

**NEW: `Add StoryVar [name]: value`** -- like `Add Variable` but also registers the variable for SugarCube save-state serialization via `Config.saves.tryDraftOnAutoSave` and `State.variables` persistence hooks.

**NEW: `[ONCE]`, `[soft]`, `[typeof:funcName]` modifiers** -- inline modifiers on Insert After/Before anchors. `[ONCE]` prevents re-injection if any mod has already injected at the same anchor. `[soft]` downgrades failure from `FailsPatchLog` to a warning. `[typeof:funcName]` wraps the injected body in a `typeof funcName !== "undefined"` guard automatically.

**NEW: `IfVersionAtLeast [x.y.z]:`** -- guard clause that gates a directive on the detected game version. Reads from the `<tw-storydata>` `ifid` or version attribute.

**NEW: `--dry-run` mode** -- runs the full parse and patch pipeline but skips writing the output file. Useful for validating a mod set without producing patched HTML.

**NEW: `--watch` mode** -- monitors the mods folder for file changes and re-patches automatically on modification. Requires `watchdog` package (graceful fallback to polling if absent).

**NEW: `Modifies:` header field** -- pre-flight warning emitted when two loaded mods declare the same target in their `Modifies:` header. Surface-level conflict detection at load time.

**NEW: Parallel mod parsing** -- mod files are parsed concurrently via `ThreadPoolExecutor`. Parse time scales with CPU count rather than mod count.

**NEW: Directive ordering warnings** -- emitted when a mod file contains directives in an order that could produce incorrect results (e.g. `Insert Into Function` before the `Add Function` it targets).

**NEW: Conflict map JSON output** -- after patching, a `conflict_map.json` is written to the logs folder listing every directive conflict detected with source mod attribution.

**NEW: `regex` engine support** -- uses the `regex` package when available for backtracking safety and possessive quantifiers. Falls back to stdlib `re` with zero API change.

**NEW: `rich` terminal output** -- styled terminal output with colour-coded log lines, progress bars, and summary tables when `rich` is installed. Graceful fallback to plain `print`.

---

### v0.7.0 and earlier

The full v0.7.0 changelog (dependency graph load ordering, Hook `around:` timing, `IfPassageContains`/`IfPassageHasTag` guards, With: auto-escape, BeautifulSoup 4 HTML layer, structured mod headers, ST_UNSCOPED advisory in KittyValidate, TOML config migration) is covered in the guides included in each platform zip.

---

## Pick your platform

### Windows

**Extract:** `KittyEcosystem_Window.v1.zip` anywhere on your computer.

**What's inside:**

| File | What it does |
|---|---|
| `KittyPatcher.exe` | The patcher -- applies all mods and opens the game |
| `KittyToolbench.exe` | GUI launcher -- validate, patch, and configure from one window |
| `KittyValidate.exe` | Pre-flight checker -- finds anchor failures before patching |
| `KittyDiffAssist.exe` | Diff tool -- generates port drafts when a mod fails (modders) |
| `KittyModConverter.exe` | Converter -- suggests stronger directives for old `.mod` files (modders) |
| `KittyPort.exe` | Port pipeline -- updates mods across game versions (modders) |
| `KittyScaffold.exe` | Scaffold generator -- creates starter `.mod` files (modders) |
| `KittyTest.exe` | Test runner -- runs assertion specs against a patched HTML (modders) |
| `KittyPatcher_v0_7_6.py` | Original Python patcher source -- for reading or tinkering |
| `KittyToolingCommon.py` | Shared Python tooling source -- required alongside the `.py` file |
| `av_libglesv2.dll` | Graphics runtime required by KittyToolbench -- do not remove |
| `libHarfBuzzSharp.dll` | Text rendering runtime required by KittyToolbench -- do not remove |
| `libSkiaSharp.dll` | Graphics rendering runtime required by KittyToolbench -- do not remove |
| `mods/cm_dependencies.json` | Dependency graph -- controls mod load order |
| `KittyPatcher_v0_7_6_Guide_G.pdf` | General guide -- setup, directives, troubleshooting |
| `KittyPatcher_v0_7_6_Guide_M.pdf` | Modder guide -- authoring, porting, advanced patterns |

The three `.dll` files are required by `KittyToolbench.exe` for its GUI rendering. They must stay in the same folder as the exe. Deleting them will prevent the Toolbench from launching.

The two `.py` files are the original Python implementation, included for anyone who wants to read the code or compare it against the C# port. They are not used by any of the executables and are not needed for normal use.

**Requirements:** Windows 10 / 11 (64-bit). No additional software required.

**Setup:**
1. Extract `KittyEcosystem_Window.v1.zip` anywhere on your computer.
2. Create a `mods/` folder next to `CourseOfTemptation.html` if it doesn't already exist.
3. Drop your `.mod` files into `mods/`.
4. Double-click `KittyPatcher.exe`.

**Running:**

Double-click `KittyPatcher.exe` -- it finds your game HTML automatically, applies all mods, and opens the patched game in your browser.

For a GUI with live log streaming, use `KittyToolbench.exe` instead.

From a terminal with verbose output:
```
KittyPatcher.exe --verbose
```

To specify the HTML path explicitly:
```
KittyPatcher.exe "C:\Games\COT\CourseOfTemptation.html"
```

To unlock the Port tab in the Toolbench (cross-version porting pipeline, for modders):
```
KittyToolbench.exe --modder
```

---

### Linux

**Extract:** `KittyEcosystem_Linux.v1.zip` anywhere on your system.

**What's inside:** The same set of tools as Windows, compiled as native Linux x64 binaries with no file extension. The `.dll` files and `.py` files are not included -- they are Windows-specific. The guide PDFs and `cm_dependencies.json` are identical.

**Requirements:** Linux x64. No additional software required. The binaries are fully self-contained.

**Setup:**
1. Extract `KittyEcosystem_Linux.v1.zip` anywhere on your system.
2. Make the binaries executable. You only need to do this once after extracting:
```bash
chmod +x KittyPatcher KittyToolbench KittyValidate KittyDiffAssist \
         KittyModConverter KittyPort KittyScaffold KittyTest
```
3. Create a `mods/` folder next to `CourseOfTemptation.html` if it doesn't already exist.
4. Drop your `.mod` files into `mods/`.
5. Run the patcher:
```bash
./KittyPatcher
```

**Running:**

```bash
./KittyPatcher                          # auto-detect game HTML, apply mods, open browser
./KittyPatcher --verbose                # verbose output
./KittyPatcher /path/to/CourseOfTemptation.html   # explicit HTML path
./KittyToolbench                        # GUI launcher
./KittyToolbench --modder              # GUI with Port tab unlocked
```

The patcher auto-detects `CourseOfTemptation.html` by searching the current directory and up to two parent levels. If it finds multiple copies it shows a numbered menu.

**Note on KittyToolbench on Linux:** The Toolbench GUI uses SkiaSharp for rendering. On some minimal Linux installs you may need `libfontconfig` and `libfreetype` installed:
```bash
# Debian / Ubuntu
sudo apt install libfontconfig1 libfreetype6

# Fedora / RHEL
sudo dnf install fontconfig freetype
```
If the Toolbench fails to launch, use the command-line tools directly -- `KittyPatcher`, `KittyValidate`, etc. all work without the GUI.

---

### macOS

**Extract:** `KittyEcosystem_Mac.v1.zip` anywhere on your system.

**What's inside:** The same set of tools as Windows, compiled as native macOS binaries (universal build supporting both Apple Silicon and Intel). The `.dll` files and `.py` files are not included. The guide PDFs and `cm_dependencies.json` are identical.

**Requirements:** macOS 12 Monterey or later. No additional software required. The binaries are fully self-contained.

**Setup:**
1. Extract `KittyEcosystem_Mac.v1.zip` anywhere on your system.
2. Make the binaries executable. You only need to do this once after extracting:
```bash
chmod +x KittyPatcher KittyToolbench KittyValidate KittyDiffAssist \
         KittyModConverter KittyPort KittyScaffold KittyTest
```
3. On first launch, macOS Gatekeeper will block unsigned binaries with a warning that the developer cannot be verified. To allow them:
   - **Option A (recommended):** Right-click the binary in Finder and choose **Open**, then confirm in the dialog. Do this once per binary you want to use.
   - **Option B:** Remove the quarantine attribute from all binaries at once from Terminal:
   ```bash
   xattr -dr com.apple.quarantine .
   ```
   Run this command from inside the extracted folder.
4. Create a `mods/` folder next to `CourseOfTemptation.html` if it doesn't already exist.
5. Drop your `.mod` files into `mods/`.
6. Run the patcher:
```bash
./KittyPatcher
```

**Running:**

```bash
./KittyPatcher                          # auto-detect game HTML, apply mods, open browser
./KittyPatcher --verbose                # verbose output
./KittyPatcher /path/to/CourseOfTemptation.html   # explicit HTML path
./KittyToolbench                        # GUI launcher
./KittyToolbench --modder              # GUI with Port tab unlocked
```

**Note on KittyToolbench on macOS:** If the Toolbench GUI fails to launch, try removing the quarantine attribute (Option B above) if you haven't already. If it still fails, use the command-line tools directly -- all patcher functionality is available without the GUI.

---

## Folder structure (inside any extracted zip)

```
CourseOfTemptation.html          <- your game (untouched)
CourseOfTemptation.patched.html  <- patched output (auto-created)
KittyPatcher[.exe]
KittyToolbench[.exe]
KittyValidate[.exe]
KittyDiffAssist[.exe]
KittyModConverter[.exe]
KittyPort[.exe]
KittyScaffold[.exe]
KittyTest[.exe]
KittyPatcher_v0_7_6_Guide_G.pdf
KittyPatcher_v0_7_6_Guide_M.pdf
[Windows only] KittyPatcher_v0_7_6.py
[Windows only] KittyToolingCommon.py
[Windows only] av_libglesv2.dll
[Windows only] libHarfBuzzSharp.dll
[Windows only] libSkiaSharp.dll
mods/
    cm_dependencies.json
    YourMod.v1.mod
    AnotherMod.v1.mod
    logs/
        MainPatchLog.txt
        ModPatchLog.txt
        FailsPatchLog.txt
        backup/
            CourseOfTemptation.html   <- clean backup, auto-created on first run
        cache/
            ...                       <- patch result cache, auto-managed
```

The `mods/logs/` folder is created automatically on first run. `backup/` and `cache/` are created inside it automatically.

---

## Mod load order

Mods are applied in dependency order automatically using `mods/cm_dependencies.json`. Parents always load before children. Within the same dependency level, the `Priority:` field in each mod's header controls order (lower number = earlier, default 1000).

To adjust load order manually, open the Toolbench, go to the **Settings** tab, and edit the list there. Without `cm_dependencies.json`, mods load in alphabetical filename order.

---

## For modders

The modder tools -- `KittyDiffAssist`, `KittyModConverter`, `KittyPort`, `KittyScaffold`, `KittyTest` -- are for anyone writing or maintaining `.mod` files. They are included in all three platform zips.

The **Port tab** in the Toolbench is hidden by default because it requires two game HTML files to operate and has no use for regular players. To show it, launch the Toolbench with `--modder`:

```
# Windows
KittyToolbench.exe --modder

# Linux / macOS
./KittyToolbench --modder
```

For full documentation on writing and porting mods, see the two guide PDFs included in each zip:

- **KittyPatcher_v0_7_6_Guide_G.pdf** -- General guide. Covers every directive, guard clause, processing order, escaping rules, and common authoring mistakes. Start here.
- **KittyPatcher_v0_7_6_Guide_M.pdf** -- Modder guide. Covers directive resilience tiers, KittyDiffAssist, KittyPort, cross-mod patterns, namespace conventions, and porting after game updates.

---

## Log files

All log files live in `mods/logs/` and are cleared and rewritten on every patch run. Copy a log before re-running if you need to preserve it for comparison.

| File | Contents |
|---|---|
| `MainPatchLog.txt` | Summary: mod count, success/fail counts, timing |
| `ModPatchLog.txt` | Every directive attempt with search key and result |
| `FailsPatchLog.txt` | Only failures and conflicts -- check this first when something breaks |
| `CustomLog.txt` | Custom messages from mod-specific logging |

---

## Troubleshooting

### All platforms

**Nothing happens / game doesn't open**
Check `mods/logs/MainPatchLog.txt` for errors at the top. Make sure `CourseOfTemptation.html` is reachable -- the patcher searches the current directory and up to two parent levels. If it cannot find the file, pass the full path explicitly:
```bash
# Windows
KittyPatcher.exe "C:\Games\COT\CourseOfTemptation.html"

# Linux / macOS
./KittyPatcher "/home/user/games/COT/CourseOfTemptation.html"
```

**A mod didn't apply**
Open `mods/logs/FailsPatchLog.txt`. Each failure lists the exact anchor that didn't match. The mod may be written for a different game version -- check with the mod author.

**"No match found" entries in FailsPatchLog.txt**
This is expected when a mod targets a different game version than the one you have. The game still launches and all other mods that did apply will work. Check with the mod author for an updated version targeting your game version.

**Game opens but something is broken**
The patcher restores from a clean backup on every run, so re-running always gives a fresh patch. If the issue persists, disable mods one at a time to find the culprit. Rename any `.mod` file to `.mod.disabled` to skip it without deleting it.

**The patched HTML was created but the game won't load in the browser**
The patched file is large (16 MB+). Chrome and Firefox handle it best. If the game loads blank or shows a JavaScript error, open the browser console (F12 on Windows/Linux, Cmd+Option+J on macOS) and check for errors -- a mod may have injected code with a syntax error. Disable mods one at a time to find the one causing it.

**"Multiple game versions found" menu**
The patcher found more than one `CourseOfTemptation.html` nearby. Enter the number for the version you want to patch, or pass the full path explicitly to skip the menu.

**The patch is slow on first run**
On the first run after any mod or game file change, the patcher applies everything from scratch. With a large mod set this can take a few minutes. Subsequent runs with the same files are near-instant because the result is cached. If startup stays slow on repeated runs, check that `kitty_config.toml` has `[cache] enabled = true`.

**Two mods are conflicting**
Open `FailsPatchLog.txt` and look for `CONFLICT DETECTED` lines. Two mods are targeting the same code -- the last mod in load order wins. To control which applies, edit `mods/cm_dependencies.json` so the preferred mod loads after the other, or check with the mod authors -- a compatibility submod may already exist.

**A mod stopped working after a game update**
The game developer changed code the mod was patching. The mod's anchor no longer exists at that location. This requires a mod update from the author. In the meantime, rename the mod to `.mod.disabled` so it skips cleanly without blocking other mods.

**Cache is stale or not being used**
The cache key covers the vanilla HTML and all `.mod` files in `mods/`. If any `.mod` file changed, the cache is automatically invalidated. If startup is slow despite no changes, confirm that `kitty_config.toml` has `[cache] enabled = true` and that no log files are loose in the `mods/` folder itself (they should be inside `mods/logs/`). Delete the `mods/logs/cache/` folder to force a full re-patch.

**The backup folder is missing**
The backup is created on the very first successful run. If you deleted it, run the patcher once with the original unmodified `CourseOfTemptation.html` in place to recreate it. Never use `CourseOfTemptation.patched.html` as your source HTML -- always use the unmodified original.

**The patcher finds the wrong HTML file**
Pass the full path explicitly on the command line. See "Nothing happens / game doesn't open" above for the syntax.

**KittyValidate reports "ambiguous" for a directive**
The anchor text appears in more than one place in the HTML. The directive will match the first occurrence, which may be the wrong one. This is a mod authoring issue -- the mod author needs a more specific anchor or a scoped directive. Report it to the mod author with the relevant KittyValidate output lines.

---

### Windows only

**KittyToolbench won't launch**
Make sure the three `.dll` files (`av_libglesv2.dll`, `libHarfBuzzSharp.dll`, `libSkiaSharp.dll`) are still in the same folder as `KittyToolbench.exe`. These are required for the GUI to start. If you moved the exe without the dlls, copy them alongside it.

**Running the `.py` source file gives an import error**
Both `KittyPatcher_v0_7_6.py` and `KittyToolingCommon.py` must be in the same folder. Also confirm Python 3.10 or later is installed (`python --version` in a terminal) and that `pip install beautifulsoup4 tomlkit` has been run. The `.py` files require Python -- the `.exe` files do not.

**Terminal window closes immediately**
Run `KittyPatcher.exe` from a Command Prompt or PowerShell window rather than double-clicking so you can read any error output before it closes.

---

### Linux only

**"Permission denied" when running a binary**
The binaries need execute permission set after extraction. Run this once from inside the extracted folder:
```bash
chmod +x KittyPatcher KittyToolbench KittyValidate KittyDiffAssist \
         KittyModConverter KittyPort KittyScaffold KittyTest
```

**KittyToolbench fails to start on Linux**
The Toolbench GUI requires `libfontconfig` and `libfreetype`. Install them if missing:
```bash
# Debian / Ubuntu / Mint
sudo apt install libfontconfig1 libfreetype6

# Fedora / RHEL / CentOS
sudo dnf install fontconfig freetype

# Arch
sudo pacman -S fontconfig freetype2
```
If the Toolbench still fails after installing those, use the command-line tools directly -- `KittyPatcher`, `KittyValidate`, and the other binaries all work without the GUI.

**Browser does not open automatically**
The patcher attempts to open the default browser via `xdg-open`. If your system does not have `xdg-open` or a default browser configured, open `CourseOfTemptation.patched.html` manually from your file manager or browser. The patch is still applied correctly even if the browser launch fails.

---

### macOS only

**"Cannot be opened because the developer cannot be verified" (Gatekeeper)**
macOS blocks unsigned binaries by default. Two ways to allow them:

- **Per binary:** Right-click the binary in Finder, choose **Open**, then confirm. Do this once for each binary you want to use.
- **All at once:** From Terminal, run this command from inside the extracted folder:
```bash
xattr -dr com.apple.quarantine .
```
After either method, the binaries run normally without further prompts.

**KittyToolbench fails to start on macOS**
Try removing the quarantine attribute first (see above). If it still fails, use the command-line tools directly -- all patcher functionality is available without the GUI.

**Browser does not open automatically**
The patcher uses `open` to launch the default browser. If the patched HTML does not open automatically, open `CourseOfTemptation.patched.html` manually from Finder or drag it into a browser window. The patch is still applied correctly.

**"Bad CPU type in executable" error**
This should not happen with the universal binary build. If it does, confirm you are on macOS 12 Monterey or later and running on either Apple Silicon or Intel -- both are supported. File a bug report if the error persists on a supported system.

---

*KittyEcosystem v1 -- KittyPatcher v0.7.6 -- Course of Temptation mod toolchain -- C# edition*
