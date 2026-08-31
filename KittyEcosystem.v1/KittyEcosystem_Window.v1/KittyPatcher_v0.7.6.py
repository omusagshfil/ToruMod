# KittyPatcher v0.7.6
# Originally created by Kitty/LK
# Updated and maintained with their permission
# Unauthorized redistribution without attribution is not permitted

"""
KittyPatcher v0.7.6
-------------------
A mod patcher for Course of Temptation (COT).
Applies .mod files to the game HTML before launch.

Original author : Kitty/LK
Maintained by   : CoderMaverick (with permission)
License         : Unauthorized redistribution without attribution is not permitted

v0.7.6 changes:
  - Bug fix: Replace: / legacy ~~/~ blocks now apply in full load order,
    including when multiple mods target the same OLD anchor.
    Previously mod_dict was a plain Python dict (str -> (new, guards)).
    dict.update() during the sequential merge phase silently overwrote
    earlier entries whenever two mods had the same OLD anchor string.
    The last mod to be merged "won" and all earlier mods' replacements
    for that anchor were permanently lost before any HTML was touched.
    This caused Bits & Fun v1.3.3f to lose 199 of its ~~ replacement
    blocks whenever other mods happened to target the same vanilla text:
    97 were overwritten by mods whose With: body was identical (those
    still produced the correct result by accident), and 102 were
    overwritten by mods whose With: body was different, so B&F's changes
    were never applied at all.  Root pattern: vanilla HTML is patched
    by mod A first, then B&F's ~~ anchor targets the original vanilla
    text which no longer exists because mod A already changed it.  With
    sequential application each mod runs against the HTML as left by all
    prior mods, so B&F's blocks run first (load order places
    Bits_Fun_V1.3.3f.mod before CM and restore mods alphabetically) and
    subsequent mods layer on top of B&F's output.
    Fix: added mod_list alongside mod_dict.  mod_list is an ordered list
    of (old_key, source_mod) tuples that records every insertion including
    duplicates.  Phase 1 application iterates mod_list in insertion order
    and looks up each entry in mod_dict for the With: body.  mod_dict is
    still used as a dict for inner-replacement (same-mod nesting) lookups,
    which do not have a cross-mod ordering concern.  When the same OLD
    anchor appears in mod_list multiple times, each entry is applied in
    sequence against the live HTML; later mods see the HTML as modified by
    earlier ones.  An ORDERING WARNING is emitted whenever mod_list
    contains duplicate OLD anchors so authors know the sequence.

v0.7.5 changes:
  - Feature: pid="auto" and position="auto" now work in legacy ~~ delimiter
    block anchors, not just in new-style Replace: and Add Passage: directives.
    Previously, EscapeTwineTags() encoded the quotes in "auto" to &quot;auto&quot;
    when storing the ~~ anchor key, so the pid="auto" retry block in
    patch_html_file (which checks for the raw form) never fired, and position
    was never resolved in anchors at all.  Fix: extended
    _resolve_pid_auto_in_anchor to handle both the raw form (pid="auto") and
    the encoded form (pid=&quot;auto&quot;) produced by EscapeTwineTags, and
    added position="auto" / position=&quot;auto&quot; resolution to the same
    function.  The function is now called immediately after _normalize_anchor
    in the Replace loop for both old_lines and _old_lines_raw, so ~~ blocks
    and new-style Replace: directives behave identically.

v0.7.4 changes:
  - Bug fix: [Mod] section header not stripped before proc_replacement_old.
    Mods using the DoggyPatcher-compatible [Mod]...bare key:value header format
    (without # prefixes) had those lines pass through the proc_replacement_old
    header-strip loop unchanged, because that loop only strips lines starting
    with #.  The [Mod] and bare key:value lines then entered the ~~/~ splitter
    as content.  If the mod body contained any ~ tilde character after those
    lines, the entire header block became the old_lines Replace: anchor,
    producing a spurious "No match found for '[Mod]\n# Name: ModName\n...'"
    failure that attributed the whole mod as failed.  Fix: the header-strip
    loop in proc_replacement_old now also tracks [Mod]..[/Mod] section state
    and skips bare key:value lines inside that section, matching the behaviour
    of _parse_mod_header.
  - Bug fix: Insert Into Object / Append Array / Insert Into Array / Append Variable
    to Class / Append Function to Class / Merge Into Object body termination.
    These struct directives used a private terminator loop that only checked other
    struct-kind tokens (_STRUCT_KINDS).  Any non-struct directive (Append To Passage,
    Add Function, Hook, Replace Function, Insert After, etc.) that appeared after a
    struct directive body was silently absorbed into the body content and injected
    verbatim into the JS script block.  In practice: CM_BC.v2.mod has an
    Insert Into Object [setup.miscitems]: that adds new condom types, immediately
    followed by Append To Passage [CMBCCreampieAftermath]:.  The Append To Passage
    header + With: + body were all injected into setup.miscitems, producing
    "Append To Passage [CMBCCreampieAftermath]:\nWith:\n<<if...>>" in raw JS.
    The JS parser hit 'To' as an unexpected identifier and aborted the entire
    script block, cascading into every setup.* function appearing as undefined.
    Fix: replaced the private struct terminator loop with _find_next_directive,
    which checks all 35 directive token types uniformly.
  - Bug fix: Insert After/Before script-block context detection.
    The batch Insert After path (v0.7.3) and the non-batch Insert After/Before
    path were missing the IsInsideScriptBlock check that the C# patcher has
    always had (PatchEngine.cs line 671-674).  When an Insert After anchor
    matched inside the <script> block (because the game version changed and
    moved that line, or the anchor text incidentally appeared there), the body
    was injected raw into JavaScript without encoding.  Passage-markup bodies
    containing <<set $foo to bar>> produced a SyntaxError: Unexpected identifier
    'To' that aborted the entire script block, cascading into every setup.*
    function appearing as undefined.  Fix: added _is_in_script_block(html, pos)
    helper (direct port of C# IsInsideScriptBlock) and applied it at all three
    injection sites.  Bodies injected into passage context are now run through
    escape_twine_tags() so <<macros>> are stored as &lt;&lt;macros&gt;&gt;;
    bodies injected into the script block remain raw JS.
  - Bug fix: Replace: anchor encoding for script-block targets.
    _normalize_anchor calls escape_twine_tags() which encodes raw quotes to
    &quot; before searching.  This is correct for passage content but wrong for
    script block content which stores raw characters.  Replace: anchors targeting
    JS object entries were silently failing with "No match found" because
    &quot;key&quot; never matches "key" in the script block.  Fix: two-pass
    search -- encoded anchor first (passage targets), raw anchor fallback when
    the encoded search misses and the anchor contains no passage tag.  Log
    message distinguishes fallback hits.
  - Hook: parameter destructuring injection.
    The wrapper function signature is now always "function()" regardless of
    the original function's parameter list.  When the original function has
    named parameters, the patcher injects
    "const [p1, p2, ...] = arguments;" at the top of the wrapper body
    (before the hook body for before:/around:, after _result assignment for
    after:).  This makes all original parameter names available by name
    inside every hook body without the author needing to know the internal
    implementation or use arguments[N] indexing.  Default values and rest
    spread prefixes (...) are stripped from param names before injection so
    the destructuring assignment is always valid JS.  Functions with zero
    parameters produce no injection.
  - Hook: local-variable static analysis warning.
    When building a Hook wrapper the patcher now scans the original function
    body for let/const/var declarations and checks whether the hook body
    references any of those names as whole-word identifiers.  If any match is
    found a HOOK WARNING is written to alllogs identifying the out-of-scope
    locals by name.  These names are inaccessible in the hook wrapper and cause
    a ReferenceError at runtime.  Parameter names (injected via destructuring)
    are excluded from the warning.

v0.7.3 changes:
  - Patch cache: content-addressed SHA-256 cache (vanilla HTML + all mod files).
    Cache hit skips the full patch phase (~4 min -> ~0.2s).  Disable via
    [cache] enabled = false in kitty_config.toml.  Cache pruned to 10 entries.
  - Patch-phase speedup: Append To Passage and Insert After/Before are now
    batched per-target.  All appends/inserts to the same passage or anchor are
    collected first, then applied in a single right-to-left pass.  Eliminates
    repeated full-HTML regex scans for the same passage (207 Append To Passage
    calls across 82 mods previously caused 207 separate O(22MB) regex passes).
  - Bug fix: cache no longer stores results when patch has failures.
    patch_html_file now returns (replacements_made, replacements_failed, failed_mods).
  - Bug fix: Hook conflict handling.  When multiple mods Hook the same function,
    the second and later hooks are no longer silently dropped.  Each additional
    hook body is appended into the existing wrapper so all mods fire.
  - Bug fix: _compute_cache_key excludes the logs/ subdirectory from the hash
    walk so log file changes don't cause spurious cache misses.
"""

__author__  = "CoderMaverick"
__credits__ = ["Kitty/LK (original creator)"]
__version__ = "0.7.6"
__license__ = "Unauthorized redistribution without attribution is not permitted"


import os
import subprocess
import platform
import shlex
import webbrowser
import html  
import sys
import shutil
import time
import hashlib
import json as _json
from concurrent.futures import ThreadPoolExecutor, as_completed
from KittyToolingCommon import is_interactive_cli, KittyConfig, resolve_mod_load_order, VALID_MOD_EXTS, _get_compiled, KittyHTMLLayer, _load_global_registry, _load_mod_sidecar, _stem, load_mod_source

# v0.7.1: use `regex` engine when available (backtracking safety, possessive
# quantifiers). Falls back to stdlib re -- zero API change.
try:
    import regex as re
    _REGEX_ENGINE = "regex"
except ImportError:
    import re
    _REGEX_ENGINE = "re"

# v0.7.1: rich for styled terminal output. Graceful fallback to plain print.
try:
    from rich.console import Console as _RichConsole
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.table import Table as _RichTable
    from rich.text import Text as _RichText
    from rich import print as _rich_print
    _RICH_AVAILABLE = True
    _console = _RichConsole()
except ImportError:
    _RICH_AVAILABLE = False
    _console = None

# v0.7.1: watchdog for --watch mode. Optional.
try:
    from watchdog.observers import Observer as _WatchdogObserver
    from watchdog.events import FileSystemEventHandler as _WatchdogHandler
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False

# ── Distribution secret ────────────────────────────────────────────────────────
# This constant is the only key material for patcher-keyed encoded mods.
# It never appears in any distributed mod file -- it lives here only.
# Changing this value will break decryption of all previously encoded mods.
_KITTY_DIST_SECRET = bytes([
    0xC4, 0x7A, 0x1E, 0x93, 0xB6, 0x2D, 0x58, 0xF1,
    0x0A, 0xE7, 0x3C, 0x94, 0x61, 0xBF, 0x27, 0x4E,
    0x85, 0x19, 0xD3, 0x6C, 0xA0, 0x52, 0xFE, 0x3B,
    0x77, 0xC8, 0x0F, 0x46, 0x9D, 0xE1, 0x23, 0x70,
])


# ------------------------------------------------
# Base directories
# ------------------------------------------------

if getattr(sys, 'frozen', False):
    script_dir = os.path.dirname(sys.executable)
    distmode = True
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    distmode = False

config_file = os.path.join(script_dir, "kitty_config.toml")
_kitty_cfg = KittyConfig(script_dir)


# ------------------------------------------------
# Verbose logging flag
# ------------------------------------------------
# --verbose or -v on the command line, or verbose=true in [logging] section
# of kitty_config.toml.  When enabled, Replace:/With: operations log the full
# old and new content.  Default off -- concise logging only.

_verbose_logging = '--verbose' in sys.argv or '-v' in sys.argv

# --dry-run: run all phases, report what would change, write nothing.
_dry_run = '--dry-run' in sys.argv

# --watch: re-patch automatically when any mod file changes.
_watch_mode = '--watch' in sys.argv

# Strip flags from argv so they don't interfere with HTML path detection
sys.argv = [a for a in sys.argv if a not in ('--verbose', '-v', '--dry-run', '--watch')]

if not _verbose_logging:
    # Check config file fallback
    _verbose_logging = _kitty_cfg.get("logging", "verbose", False)

# ------------------------------------------------
# Detect HTML location
# ------------------------------------------------

html_file = None

# HTML passed via command argument -- skip menu
if len(sys.argv) > 1:
    html_file = os.path.abspath(sys.argv[1])

else:
    # Collect all CourseOfTemptation.html candidates up to two parent levels
    _candidates = []
    _seen = set()

    _search_roots = [
        script_dir,
        os.path.abspath(os.path.join(script_dir, "..")),
        os.path.abspath(os.path.join(script_dir, "..", "..")),
    ]

    def _walk_html_candidates(root, max_depth=3):
        root = os.path.abspath(root)
        for current_root, _dirs, files in os.walk(root, topdown=True):
            _dirs.sort()
            files.sort()
            rel = os.path.relpath(current_root, root)
            depth = 0 if rel == '.' else rel.count(os.sep) + 1
            if depth >= max_depth:
                _dirs[:] = []
            if "CourseOfTemptation.html" in files:
                yield os.path.join(current_root, "CourseOfTemptation.html")

    for _root in _search_roots:
        try:
            for _path in _walk_html_candidates(_root, max_depth=3):
                _norm = os.path.normcase(os.path.abspath(_path))
                if _norm not in _seen:
                    _candidates.append(_path)
                    _seen.add(_norm)
        except PermissionError:
            pass

    if not _candidates:
        raise FileNotFoundError(
            "CourseOfTemptation.html could not be located. "
            "Place the patcher in or near the game folder, or pass the HTML path as an argument."
        )
    elif len(_candidates) == 1:
        html_file = _candidates[0]
    else:
        # Multiple versions found -- present a numbered menu
        print("\nMultiple game versions found. Select one to patch:\n")
        for _i, _c in enumerate(_candidates, 1):
            try:
                _label = os.path.relpath(_c, script_dir)
            except ValueError:
                _label = _c  # Different drive on Windows
            print(f"  [{_i}] {_label}")
        print()
        while True:
            try:
                _choice = input(f"Enter number (1-{len(_candidates)}): ").strip()
                _idx = int(_choice) - 1
                if 0 <= _idx < len(_candidates):
                    html_file = _candidates[_idx]
                    break
                print(f"  Please enter a number between 1 and {len(_candidates)}.")
            except EOFError:
                raise RuntimeError("No interactive input available for version selection.")
            except ValueError:
                print("  Invalid input.")


# Base directory becomes the HTML folder
base_dir = os.path.dirname(html_file)

# Output file: original stays untouched, patched result written here
patched_file = os.path.join(
    base_dir,
    os.path.splitext(os.path.basename(html_file))[0] + '.patched.html'
)


# ------------------------------------------------
# Mods folder
# ------------------------------------------------

mods_folder = os.path.join(base_dir, "mods")


# ------------------------------------------------
# Logs
# ------------------------------------------------

logs_folder = os.path.join(mods_folder, "logs")
backup_folder = os.path.join(logs_folder, "backup")

mainlog_file = os.path.join(logs_folder, "MainPatchLog.txt")
log_file = os.path.join(logs_folder, "ModPatchLog.txt")
faillog_file = os.path.join(logs_folder, "FailsPatchLog.txt")
customlog_file = os.path.join(logs_folder, "CustomLog.txt")


# ------------------------------------------------
# Cache
# ------------------------------------------------

cache_dir = os.path.join(logs_folder, "cache")


# ------------------------------------------------
# Patch cache (v0.7.3)
# ------------------------------------------------
# Content-addressed cache keyed on SHA-256(vanilla HTML bytes + sorted mod file
# paths + mod file bytes).  On a cache hit the full load+patch phases are skipped
# and the cached patched HTML is copied directly to the output file (~0.2s vs
# ~4 min).  Cache is invalidated automatically on any content or filename change.
#
# Disable: [cache] enabled = false in kitty_config.toml.
# Files:   mods/logs/cache/<digest>.patched.html
#          mods/logs/cache/<digest>.meta.json
# Pruning: keeps 10 most recently written entries.

_CACHE_HASH_ALGO   = "sha256"
_CACHE_META_SUFFIX = ".meta.json"
_CACHE_HTML_SUFFIX = ".patched.html"


def _cache_enabled() -> bool:
    return bool(_kitty_cfg.get("cache", "enabled", True))


def _compute_cache_key(html_file: str, mods_folder: str) -> str:
    """SHA-256 over (vanilla HTML + sorted mod file rel-paths + contents).
    Excludes the logs/ subdirectory so log writes never cause cache misses."""
    h = hashlib.new(_CACHE_HASH_ALGO)
    try:
        with open(html_file, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    logs_abs = os.path.normcase(os.path.abspath(logs_folder))
    mod_paths = []
    if os.path.isdir(mods_folder):
        for root, dirs, files in os.walk(mods_folder):
            # Skip the logs subtree entirely so log/cache files don't affect the key
            dirs[:] = sorted(
                d for d in dirs
                if os.path.normcase(os.path.abspath(os.path.join(root, d))) != logs_abs
            )
            for fname in sorted(files):
                if any(fname.endswith(ext) for ext in VALID_MOD_EXTS):
                    mod_paths.append(os.path.join(root, fname))
    for mp in sorted(mod_paths):
        h.update(os.path.relpath(mp, mods_folder).encode("utf-8"))
        try:
            with open(mp, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 16), b""):
                    h.update(chunk)
        except OSError:
            return ""
    return h.hexdigest()


def _cache_lookup(cache_key: str):
    """Return cached patched HTML path if valid entry exists, else None."""
    if not cache_key:
        return None
    html_path = os.path.join(cache_dir, cache_key + _CACHE_HTML_SUFFIX)
    meta_path = os.path.join(cache_dir, cache_key + _CACHE_META_SUFFIX)
    if os.path.exists(html_path) and os.path.exists(meta_path):
        return html_path
    return None


def _cache_store(cache_key: str, patched_html_content: str, mod_list: list):
    """Write patched HTML + metadata to cache.  Silent no-op on any error."""
    if not cache_key:
        return
    try:
        html_path = os.path.join(cache_dir, cache_key + _CACHE_HTML_SUFFIX)
        meta_path = os.path.join(cache_dir, cache_key + _CACHE_META_SUFFIX)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(patched_html_content)
        meta = {
            "key":     cache_key,
            "algo":    _CACHE_HASH_ALGO,
            "mods":    mod_list,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            _json.dump(meta, f, indent=2)
    except Exception:
        pass


def _cache_prune(keep_key: str, max_entries: int = 10):
    """Evict oldest cache entries beyond max_entries.  Never evicts keep_key."""
    try:
        entries = []
        for fname in os.listdir(cache_dir):
            if fname.endswith(_CACHE_HTML_SUFFIX):
                fpath = os.path.join(cache_dir, fname)
                entries.append((os.path.getmtime(fpath), fname))
        entries.sort(reverse=True)
        keep_fname = keep_key + _CACHE_HTML_SUFFIX
        for _mtime, fname in entries[max_entries:]:
            if fname == keep_fname:
                continue
            key = fname[: -len(_CACHE_HTML_SUFFIX)]
            for suffix in (_CACHE_HTML_SUFFIX, _CACHE_META_SUFFIX):
                try:
                    os.remove(os.path.join(cache_dir, key + suffix))
                except OSError:
                    pass
    except Exception:
        pass


def running_from_cli():
    return is_interactive_cli()
    
#Function to Create the Log Directory if it Doesn't Exist
def create_directories():
    try:
        if not os.path.exists(mods_folder):
            os.makedirs(mods_folder)
            
        if not os.path.exists(logs_folder):
            os.makedirs(logs_folder)
            
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
            
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
                
    except Exception as e:
        handle_output(f"An error occurred: {e}", "console")
        raise
        

    
#Function to Launch the HTML File in the Default Browser

# Browser identity map -- substring matched against exe path (lowercase)
# Order matters: more specific entries first (e.g. "msedge" before "edge")
_BROWSER_IDENTITY = [
    ("msedge",          "Edge",               True),
    ("microsoft edge",  "Edge",               True),
    ("chrome",          "Chrome",             True),
    ("brave",           "Brave",              True),
    ("vivaldi",         "Vivaldi",            True),
    ("chromium",        "Chromium",           True),
    ("thorium",         "Thorium",            True),
    ("ungoogled",       "Ungoogled Chromium", True),
    ("arc",             "Arc",               True),
    ("whale",           "Whale",             True),
    ("yandex",          "Yandex",            True),
    ("opera",           "Opera",             True),
    ("firefox",         "Firefox",           False),
    ("librewolf",       "LibreWolf",         False),
    ("waterfox",        "Waterfox",          False),
    ("safari",          "Safari",            False),
]

def _classify_browser(path):
    """Return (display_name, is_chromium) by matching path against _BROWSER_IDENTITY."""
    lower = path.lower()
    for fragment, name, is_chromium in _BROWSER_IDENTITY:
        if fragment in lower:
            return name, is_chromium
    # Unknown browser -- treat as non-chromium to avoid passing unsupported flags
    basename = os.path.splitext(os.path.basename(path))[0]
    return basename.capitalize(), False


def _get_browser_paths():
    """
    Return list of (display_name, executable_path, is_chromium) for all
    browsers found on this machine.

    Windows: scans the registry (HKLM + HKCU StartMenuInternet) so any
             installed browser is found regardless of install location,
             with hardcoded fallbacks for non-registering installs.
    macOS:   scans /Applications and ~/Applications for known .app bundles.
    Linux:   uses shutil.which against an expanded list of known exe names.
    """
    if sys.platform.startswith('win'):
        return _get_browser_paths_win()
    elif sys.platform.startswith('darwin'):
        return _get_browser_paths_mac()
    else:
        return _get_browser_paths_linux()


def _get_browser_paths_win():
    """Scan Windows registry for installed browsers plus hardcoded fallbacks."""
    found = []
    seen_paths = set()

    try:
        import winreg
        reg_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Clients\StartMenuInternet"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Clients\StartMenuInternet"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Clients\StartMenuInternet"),
        ]
        for hive, reg_path in reg_roots:
            try:
                key = winreg.OpenKey(hive, reg_path)
                i = 0
                while True:
                    try:
                        browser_key_name = winreg.EnumKey(key, i)
                        i += 1
                        try:
                            cmd_key = winreg.OpenKey(
                                key, browser_key_name + r"\shell\open\command"
                            )
                            exe_raw, _ = winreg.QueryValueEx(cmd_key, "")
                            winreg.CloseKey(cmd_key)
                            # Strip surrounding quotes and trailing arguments
                            exe = re.sub(r'^"([^"]+)".*$', r'\1', exe_raw.strip())
                            exe = re.sub(r"^'([^']+)'.*$", r'\1', exe.strip())
                            if ' ' in exe and not exe_raw.strip().startswith('"'):
                                exe = exe.split()[0]
                            norm = os.path.normcase(os.path.abspath(exe))
                            if os.path.exists(exe) and norm not in seen_paths:
                                name, is_chromium = _classify_browser(exe)
                                found.append((name, exe, is_chromium))
                                seen_paths.add(norm)
                        except OSError:
                            pass
                    except OSError:
                        break
                winreg.CloseKey(key)
            except OSError:
                pass
    except ImportError:
        pass

    # Hardcoded fallbacks for browsers that don't register in StartMenuInternet
    fallbacks = [
        (r"C:\Program Files\Google\Chrome\Application\chrome.exe",                True),
        (r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",          True),
        (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",               True),
        (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",         True),
        (r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",   True),
        (r"C:\Program Files\Mozilla Firefox\firefox.exe",                          False),
        (r"C:\Program Files\Opera\launcher.exe",                                   True),
        (r"C:\Program Files\Vivaldi\Application\vivaldi.exe",                      True),
        (r"C:\Program Files\Waterfox\waterfox.exe",                                False),
        (r"C:\Program Files\LibreWolf\librewolf.exe",                              False),
    ]
    for exe, is_chromium in fallbacks:
        norm = os.path.normcase(os.path.abspath(exe))
        if os.path.exists(exe) and norm not in seen_paths:
            name, _ = _classify_browser(exe)
            found.append((name, exe, is_chromium))
            seen_paths.add(norm)

    return found


def _get_browser_paths_mac():
    """Scan /Applications and ~/Applications for browser .app bundles on macOS."""
    found = []
    seen_paths = set()

    # (app bundle name, display name, is_chromium, exe name inside MacOS/)
    # exe name is None when it matches the app bundle name without .app
    known_apps = [
        ("Google Chrome.app",    "Chrome",    True,  "Google Chrome"),
        ("Microsoft Edge.app",   "Edge",      True,  "Microsoft Edge"),
        ("Brave Browser.app",    "Brave",     True,  "Brave Browser"),
        ("Firefox.app",          "Firefox",   False, "firefox"),
        ("Opera.app",            "Opera",     True,  "Opera"),
        ("Vivaldi.app",          "Vivaldi",   True,  "Vivaldi"),
        ("Safari.app",           "Safari",    False, "Safari"),
        ("Chromium.app",         "Chromium",  True,  "Chromium"),
        ("LibreWolf.app",        "LibreWolf", False, "librewolf"),
        ("Waterfox.app",         "Waterfox",  False, "Waterfox"),
        ("Arc.app",              "Arc",       True,  "Arc"),
        ("Whale.app",            "Whale",     True,  "Whale"),
        ("Yandex.app",           "Yandex",    True,  "Yandex"),
        ("Thorium.app",          "Thorium",   True,  "Thorium"),
    ]

    search_dirs = ["/Applications", os.path.expanduser("~/Applications")]

    for app_name, display_name, is_chromium, exe_name in known_apps:
        for base_dir in search_dirs:
            app_path = os.path.join(base_dir, app_name)
            exe_path = os.path.join(app_path, "Contents", "MacOS", exe_name)
            if not os.path.exists(exe_path):
                # Some apps capitalise or lowercase differently
                exe_path_alt = os.path.join(app_path, "Contents", "MacOS", exe_name.lower())
                if os.path.exists(exe_path_alt):
                    exe_path = exe_path_alt
            norm = os.path.normcase(exe_path)
            if os.path.exists(exe_path) and norm not in seen_paths:
                found.append((display_name, exe_path, is_chromium))
                seen_paths.add(norm)
                break  # found in first dir, skip second to avoid duplicates

    return found


def _get_browser_paths_linux():
    """Find browsers on Linux via PATH using shutil.which."""
    candidates = [
        ("google-chrome",          "Chrome",             True),
        ("google-chrome-stable",   "Chrome",             True),
        ("google-chrome-beta",     "Chrome Beta",        True),
        ("chromium-browser",       "Chromium",           True),
        ("chromium",               "Chromium",           True),
        ("brave-browser",          "Brave",              True),
        ("microsoft-edge",         "Edge",               True),
        ("microsoft-edge-stable",  "Edge",               True),
        ("firefox",                "Firefox",            False),
        ("firefox-esr",            "Firefox ESR",        False),
        ("librewolf",              "LibreWolf",          False),
        ("waterfox",               "Waterfox",           False),
        ("opera",                  "Opera",              True),
        ("vivaldi",                "Vivaldi",            True),
        ("vivaldi-stable",         "Vivaldi",            True),
        ("thorium-browser",        "Thorium",            True),
        ("yandex-browser",         "Yandex",             True),
        ("whale",                  "Whale",              True),
    ]
    found = []
    seen_names = set()
    seen_paths = set()
    for cmd, display_name, is_chromium in candidates:
        path = shutil.which(cmd)
        if path:
            norm = os.path.normcase(os.path.realpath(path))
            if display_name not in seen_names and norm not in seen_paths:
                found.append((display_name, path, is_chromium))
                seen_names.add(display_name)
                seen_paths.add(norm)
    return found


def _load_browser_config():
    """Return (display_name, path, is_chromium) from config, or None if not set / invalid."""
    name     = _kitty_cfg.get("browser", "name", None)
    path     = _kitty_cfg.get("browser", "path", None)
    chromium = _kitty_cfg.get("browser", "chromium", True)
    if name and path and os.path.exists(path):
        return (name, path, bool(chromium))
    return None


def _save_browser_config(name, path, is_chromium):
    _kitty_cfg.set("browser", "name", name)
    _kitty_cfg.set("browser", "path", path)
    _kitty_cfg.set("browser", "chromium", bool(is_chromium))
    _kitty_cfg.save()


def _select_browser():
    """
    Prompt the user to choose a browser from installed options.
    Saves the choice to kitty_config.toml for future runs.
    Returns (display_name, path, is_chromium) or None.
    """
    available = [(n, p, c) for n, p, c in _get_browser_paths() if os.path.exists(p)]
    if not available:
        return None

    print("\nSelect browser to open patched HTML:")
    for i, (name, _, _) in enumerate(available, 1):
        print(f"  [{i}] {name}")
    print(f"  [{len(available)+1}] System default")

    while True:
        try:
            choice = int(input(f"Enter number (1-{len(available)+1}): ").strip())
        except (ValueError, EOFError):
            choice = -1
        if 1 <= choice <= len(available):
            chosen = available[choice - 1]
            _save_browser_config(*chosen)
            print(f"Browser set to {chosen[0]}. Saved to kitty_config.toml.")
            return chosen
        elif choice == len(available) + 1:
            _save_browser_config("system default", "", False)
            print("Using system default browser. Saved to kitty_config.toml.")
            return None
        print(f"Please enter a number between 1 and {len(available)+1}.")


def _launch_browser(path, is_chromium, html_file):
    """Launch the given browser executable with the HTML file."""
    abs_path = os.path.abspath(html_file)
    if sys.platform.startswith("win"):
        url = "file:///" + abs_path.replace("\\", "/")
    else:
        url = "file://" + abs_path

    # Safari does not support Chromium flags and handles local file://
    # access differently -- route it through webbrowser.open instead.
    if "safari" in path.lower():
        webbrowser.open(url)
        return

    if is_chromium:
        # --allow-file-access-from-files: lets the local HTML load other
        # local file:// resources without being blocked by the browser's
        # same-origin policy. Without this flag COT spins on load after
        # the security dialog is dismissed.
        cmd = [path, "--allow-file-access-from-files", f"--app={url}"]
    else:
        cmd = [path, url]
    subprocess.Popen(cmd)


def open_in_browser(html_file):
    if not os.path.isfile(html_file):
        handle_output(f"The HTML file does not exist: {html_file}", "console")
        return

    # Try saved config first
    saved = _load_browser_config()

    if saved is None:
        # No valid config -- check if user previously chose system default
        if _kitty_cfg.has_section("browser") and _kitty_cfg.get("browser", "name", "") == "system default":
            webbrowser.open(("file:///" if sys.platform.startswith("win") else "file://") + os.path.abspath(html_file).replace(os.sep, "/"))
            return
        # First run or stale config -- prompt
        saved = _select_browser()

    if saved is None:
        # User chose system default (just now or previously)
        webbrowser.open(("file:///" if sys.platform.startswith("win") else "file://") + os.path.abspath(html_file).replace(os.sep, "/"))
        return

    name, path, is_chromium = saved
    try:
        _launch_browser(path, is_chromium, os.path.abspath(html_file))
    except Exception as e:
        handle_output(f"Failed to launch {name}: {e}. Falling back to system default.", "console")
        webbrowser.open(("file:///" if sys.platform.startswith("win") else "file://") + os.path.abspath(html_file).replace(os.sep, "/"))

#Function to Handle Logging and Console Output
def handle_output(message, output_type=""):
    locconsole = "console"
        
    if output_type == "log":
        log_message(message, "mod")
    elif output_type == locconsole:
        print_to_console(message)
    elif output_type == "alllogs":
        # alllogs goes to both MainPatchLog and ModPatchLog
        log_message(message, "main")
        log_message(message, "mod")
    elif output_type == "all":
        log_message(message, "mod")
    elif output_type == "failed":
        log_message(message, "failed")
     
#Function to Log Messages to a File
# v0.7.2: log buffering -- accumulate log lines in memory, flush at sync points
# instead of opening/closing the log file on every handle_output call.
_log_buffer = {'main': [], 'mod': [], 'failed': []}

def flush_logs():
    """Write all buffered log lines to disk."""
    _log_file_map = {'main': mainlog_file, 'mod': log_file, 'failed': faillog_file}
    for log_type, lines in _log_buffer.items():
        if lines:
            try:
                with open(_log_file_map[log_type], 'a', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
            except OSError:
                pass
            lines.clear()

def log_message(message, log_type="mod"):
    if log_type == "main":
        _log_buffer['main'].append(message)
    elif log_type == "mod":
        _log_buffer['mod'].append(message)
    elif log_type == "failed":
        _log_buffer['failed'].append(message)
    elif log_type == "_FLUSH":
        flush_logs()
        return
    # All writes go through the buffer -- nothing writes directly to disk here.

#Function to Print Messages to the Console
def print_to_console(message):
    if not _RICH_AVAILABLE:
        print(message)
        return
    # v0.7.1: apply rich styling based on message content
    msg_lower = message.lower()
    if any(k in msg_lower for k in ('error', 'failed', 'conflict detected', 'namespace warning', 'ordering warning')):
        _console.print(f"[bold red]{message}[/bold red]")
    elif any(k in msg_lower for k in ('warning', 'warn', '[soft]')):
        _console.print(f"[yellow]{message}[/yellow]")
    elif any(k in msg_lower for k in ('complete', 'success', 'injected', 'patched')):
        _console.print(f"[green]{message}[/green]")
    elif any(k in msg_lower for k in ('dry-run', 'dry run')):
        _console.print(f"[bold cyan]{message}[/bold cyan]")
    else:
        _console.print(message)

#Function to Clear Logs
def clear_logs():
    with open(mainlog_file, 'w') as log:
        pass  
    with open(log_file, 'w') as log:
        pass  
    with open(faillog_file, 'w') as log:
        pass

# ------------------------------------------------
# Per-injection tag balance checker
# ------------------------------------------------

_VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
}

_TWINE_PAIRS = [
    ('<<if',        '<</if>>'),
    ('<<for',       '<</for>>'),
    ('<<switch',    '<</switch>>'),
    ('<<widget',    '<</widget>>'),
    ('<<link',      '<</link>>'),
    ('<<capture',   '<</capture>>'),
    ('<<highlight', '<</highlight>>'),
    ('<<known',     '<</known>>'),
]

def _count_twine_open(text, open_tok):
    """Count open-macro occurrences, excluding close variants like <</if>>."""
    count = 0
    idx = 0
    while True:
        idx = text.find(open_tok, idx)
        if idx == -1:
            break
        next_ch = text[idx + len(open_tok)] if idx + len(open_tok) < len(text) else ''
        if next_ch != '/':
            count += 1
        idx += len(open_tok)
    return count

def _extract_passage_body(html_content, match_pos):
    """Return (passage_name, body_text) for the tw-passagedata containing match_pos,
    or (None, None) if match_pos is outside any passage (e.g. in a script block)."""
    open_idx = html_content.rfind('<tw-passagedata', 0, match_pos)
    if open_idx == -1:
        return None, None
    tag_end = html_content.find('>', open_idx)
    if tag_end == -1:
        return None, None
    close_idx = html_content.find('</tw-passagedata>', tag_end)
    if close_idx == -1 or match_pos > close_idx:
        return None, None
    name_m = re.search(r'name="([^"]+)"', html_content[open_idx:tag_end + 1])
    name = name_m.group(1) if name_m else '(unknown)'
    return name, html_content[tag_end + 1:close_idx]

def check_injection_tag_balance(html_content, match_pos, mod_label):
    """Check the passage containing match_pos for Twine macro and HTML tag imbalances.
    Returns a list of warning strings (empty if fully balanced)."""
    name, body = _extract_passage_body(html_content, match_pos)
    if body is None:
        return []

    warnings = []

    # Twine macro balance
    for open_tok, close_tok in _TWINE_PAIRS:
        opens  = _count_twine_open(body, open_tok)
        closes = body.count(close_tok)
        if opens != closes:
            warnings.append(
                f"  TAG IMBALANCE in '{name}' [{mod_label}]: "
                f"{open_tok}>> opens={opens} closes={closes} (diff={opens - closes:+d})"
            )

    # HTML element balance (skip void elements and self-closing tags)
    tag_counts = {}
    for m in re.finditer(r'<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*/?>'  , body, re.IGNORECASE):
        tag = m.group(1).lower()
        if tag not in _VOID_ELEMENTS and not m.group(0).endswith('/>'):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    for m in re.finditer(r'</([a-zA-Z][a-zA-Z0-9]*)\s*>', body, re.IGNORECASE):
        tag = m.group(1).lower()
        if tag not in _VOID_ELEMENTS:
            tag_counts[tag] = tag_counts.get(tag, 0) - 1
    for tag, delta in tag_counts.items():
        if delta != 0:
            warnings.append(
                f"  TAG IMBALANCE in '{name}' [{mod_label}]: "
                f"<{tag}> net={delta:+d} "
                f"({'unclosed' if delta > 0 else 'extra close'})"
            )

    return warnings

#Function to Escape Twine Tags by Replacing << and >> with &lt;&lt; and &gt;&gt;
def _escape_twine_region(content):
    """
    Core escape logic for a single region of text that is NOT inside a
    <<script>>...<</script>> block. Escapes << >> to &lt;&lt; &gt;&gt;
    and HTML-escapes the result with fixups for double-encoded entities.
    """
    new_content = re.sub(r'<<(.*?)>>', r'&lt;&lt;\1&gt;&gt;', content)

    if new_content != content:
        new_content = html.escape(new_content)

        new_content = new_content.replace('&amp;lt;', '&lt;')
        new_content = new_content.replace('&amp;gt;', '&gt;')
        new_content = new_content.replace('&amp;quot;', '&quot;')
        new_content = new_content.replace('&amp;amp;', '&amp;')
        new_content = new_content.replace('&#x27;', '&#39;')

        # Unescape <tw-passagedata ...> and </tw-passagedata> opening/closing tags.
        # Use [^>] so the pattern spans &quot; inside attribute values (e.g. pid="auto").
        # The old two-pass approach used [^&] which stopped at & in &quot;, leaving
        # the tag escaped and invisible to _renormalize_pids.
        new_content = re.sub(
            r'&lt;/?tw-passagedata(?:&gt;|[^>]*?&gt;)',
            lambda m: html.unescape(m.group(0)),
            new_content,
            flags=re.DOTALL
        )

        return new_content

    return content


def escape_twine_tags(content):
    """
    Escape Twine << >> macros to &lt;&lt; &gt;&gt; for HTML storage, but
    preserve content inside <<script>>...<</script>> blocks untouched.

    Script blocks contain raw JavaScript where << and >> may appear as
    operators (bitshift, template literals, comparisons). Escaping those
    would corrupt the JS. The split-and-reassemble approach (adapted from
    DoggyPatcher's ProcessPassage pattern) ensures only non-script regions
    are transformed.

    Both escaped (&lt;&lt;script&gt;&gt;) and unescaped (<<script>>) forms
    of the script tag boundaries are handled so this works regardless of
    whether the content has already been partially escaped.
    """
    # Try both raw and escaped forms of script tags
    script_open_raw  = '<<script>>'
    script_close_raw = '<</script>>'
    script_open_esc  = '&lt;&lt;script&gt;&gt;'
    script_close_esc = '&lt;&lt;/script&gt;&gt;'

    # Determine which form is present (if any)
    if script_open_raw in content:
        tag_open  = script_open_raw
        tag_close = script_close_raw
    elif script_open_esc in content:
        tag_open  = script_open_esc
        tag_close = script_close_esc
    else:
        # No script blocks -- process the entire content as one region
        return _escape_twine_region(content)

    # Split on script open tags, process non-script regions only
    parts = content.split(tag_open)
    result = []

    # When script tags are raw (<<script>>), the tag delimiters need escaping
    # to &lt;&lt;script&gt;&gt; for SugarCube passage storage, but the JS body
    # inside must stay untouched (it may contain << >> as bitshift operators).
    emit_open  = script_open_esc
    emit_close = script_close_esc

    for i, part in enumerate(parts):
        if i == 0:
            # Before the first <<script>> -- always a non-script region
            result.append(_escape_twine_region(part))
        else:
            # After a <<script>> open -- find the matching close
            close_idx = part.find(tag_close)
            if close_idx >= 0:
                # Script content (untouched) + close tag + rest (escaped)
                script_body = part[:close_idx]
                after_close = part[close_idx + len(tag_close):]
                result.append(emit_open + script_body + emit_close + _escape_twine_region(after_close))
            else:
                # No close found -- treat everything as script content (untouched)
                result.append(emit_open + part)

    return ''.join(result)

# ------------------------------------------------
# Feature: [to] Regex Auto-Fill Search
# ------------------------------------------------

def update_old_lines_from_html(old_lines, html_content):
    """
    If old_lines contains the marker "[to]", split on it to get a prefix and
    suffix, then search html_content for a substring that starts with prefix
    and ends with suffix.  The extracted content fills the gap, so the final
    old_lines becomes prefix + <whatever was in the HTML> + suffix.

    Returns old_lines unchanged when the marker is absent or no match is found.
    """
    marker = "[to]"
    if marker not in old_lines:
        return old_lines

    prefix, suffix = old_lines.split(marker, 1)
    pattern = re.escape(prefix) + r'(.*?)' + re.escape(suffix)
    match = re.search(pattern, html_content, re.DOTALL)
    if match:
        return prefix + match.group(1) + suffix
    return old_lines

# ------------------------------------------------
# Feature: Auto-escape full tw-passagedata bodies
# ------------------------------------------------

def auto_escape_passage_bodies(new_lines):
    """
    Scans new_lines for complete <tw-passagedata ...> ... </tw-passagedata>
    blocks.  For each block the body (everything after the closing '>' of the
    opening tag up to </tw-passagedata>) is HTML-escaped only when it
    contains raw Twine macros (i.e. '<<' or '>>') and is not already escaped
    (i.e. does not already contain '&lt;&lt;').

    Content inside <<script>>...<</script>> blocks is never escaped -- those
    contain raw JavaScript where << and >> are valid operators.

    This means mod authors can write either:
      - plain Twine code inside a passage  ->  auto-escaped
      - already-escaped HTML               ->  left alone
      - <<script>> blocks                  ->  left alone (JS content)
    """
    tw_block_re = _get_compiled(
        r'(<tw-passagedata\b[^>]*>)(.*?)(</tw-passagedata>)',
        re.DOTALL
    )

    def _escape_non_script_body(body):
        """Escape a passage body, preserving <<script>> regions."""
        if '<<script>>' not in body:
            return html.escape(body)

        parts = body.split('<<script>>')
        result = []
        for i, part in enumerate(parts):
            if i == 0:
                result.append(html.escape(part))
            else:
                close_idx = part.find('<</script>>')
                if close_idx >= 0:
                    script_body = part[:close_idx]
                    after = part[close_idx + len('<</script>>'):]
                    result.append('<<script>>' + script_body + '<</script>>' + html.escape(after))
                else:
                    result.append('<<script>>' + part)
        return ''.join(result)

    def maybe_escape_body(m):
        open_tag = m.group(1)
        body     = m.group(2)
        close    = m.group(3)

        # Already escaped -- leave it alone
        if '&lt;&lt;' in body or '&lt;' in body:
            return m.group(0)

        # Contains raw Twine macros -- escape non-script regions only
        if '<<' in body or '>>' in body:
            body = _escape_non_script_body(body)

        return open_tag + body + close

    return tw_block_re.sub(maybe_escape_body, new_lines)

# ------------------------------------------------
# Add Passage support (ported from v0.1.5c)
# ------------------------------------------------

#Function to Escape HTML Inside <e>...</e> Blocks Within Mod Content
def escape_html_between_tags(text, start_tag="<e>", end_tag="</e>"):
    """
    Escapes HTML characters only within blocks delimited by lines that are exactly
    start_tag and end_tag (default <e> / </e>).  The delimiter lines are consumed
    (not included in the output).

    If a directive keyword (Replace:, With:, Add Passage:, etc.) is encountered
    while inside a tag block the block is terminated immediately.

    Content that is already escaped (contains &lt; or &quot;) is left alone.
    """
    result = []
    inside = False
    buffer = []
    control_keywords = ["Replace:", "ReplaceReg [", "With:", "With{", "IfExists [",
                        "IfNotExists [", "IfRegExists [", "IfRegNotExists [",
                        "Add Passage:", "Add Javascript", "Add CSS:", "Add Events:",
                        "Append Array [", "Append Variable to Class [",
                        "Append Function to Class [", "Add Function ["]

    lines = text.split("\n")
    for line in lines:
        stripped_line = line.strip()

        # Flush buffer and exit tag-block on directive keyword
        if any(kw in stripped_line for kw in control_keywords):
            if inside:
                content = "\n".join(buffer)
                result.append(content if ("&lt;" in content or "&quot;" in content)
                               else html.escape(content))
                buffer = []
                inside = False
            result.append(line)
            continue

        if stripped_line == start_tag:
            inside = True
            continue

        if stripped_line == end_tag:
            if inside:
                content = "\n".join(buffer)
                result.append(content if ("&lt;" in content or "&quot;" in content)
                               else html.escape(content))
                buffer = []
                inside = False
            else:
                result.append(line)
            continue

        if inside:
            buffer.append(line)
        else:
            result.append(line)

    # Flush any remaining open block
    if inside:
        content = "\n".join(buffer)
        # Do not re-escape if already escaped or contains raw SugarCube macros
        if "&lt;" in content or "&quot;" in content or "<<" in content:
            result.append(content)
        else:
            result.append(html.escape(content))

    return "\n".join(result)


# ------------------------------------------------
# Mod Processing Functions
# ------------------------------------------------

#Function to Process Mod Files Using the Old Technique
def proc_replacement_old(mod_content, mod_dict, mod_list, mod_file_indexes, mod_file, conflict_map=None, key_to_mod=None): 
    # v0.7.1: Prepare mod content for legacy ~~/~ delimiter splitting.
    # Instead of stripping /* */ comments (which corrupted OLD anchors that
    # contained comments -- e.g. vanilla section markers like
    # /* twine-user-stylesheet #3: "input_range.css" */ or commented-out
    # debug blocks inside function bodies), we only neutralise ~ characters
    # INSIDE /* */ comments so they cannot misfire as ~~/~ delimiters.
    # The comment text is preserved so OLD anchors match the HTML exactly.
    _TILDE_PH = '\x00TILDE\x00'
    # v0.7.6: Strip [Mod] section header lines in addition to # comment lines.
    # The [Mod] section (DoggyPatcher-compatible header format) uses bare key:value
    # lines inside a [Mod]...[/Mod] or unterminated [Mod] block.  These are NOT
    # prefixed with # so the old header-strip loop did not remove them.  When they
    # reached the ~~/~ splitter they were treated as Replace: targets, producing
    # spurious "No match found for '[Mod]\n# Name: ...' " failures.
    _in_mod_section = False
    sanitized_lines = []
    header_done = False
    for line in mod_content.splitlines(keepends=True):
        stripped = line.strip()
        if not header_done:
            if stripped == '[Mod]':
                _in_mod_section = True
                continue
            if stripped == '[/Mod]':
                _in_mod_section = False
                continue
            if _in_mod_section:
                continue  # bare key:value inside [Mod] section
            if stripped.startswith('#') or stripped == '':
                continue
            header_done = True
        sanitized_lines.append(line)
    sanitized = ''.join(sanitized_lines)
    # 2. Neutralise ~ inside /* */ comments -- replace with placeholder, not strip
    def _escape_tildes_in_comment(m):
        return m.group(0).replace('~', _TILDE_PH)
    sanitized = re.sub(r'/\*.*?\*/', _escape_tildes_in_comment, sanitized, flags=re.DOTALL)

    replacements = sanitized.split('~~')  # Split by '~~' for multiple replacements
    for replacement in replacements:
        if '~' in replacement:
            old_lines, new_lines = replacement.split('~', 1)  # Split at single tilde
            # v0.7.1: Restore any ~ characters that were neutralised inside /* */ comments
            # before the split.  Both OLD and NEW must be restored so OLD matches the
            # HTML and NEW injects the correct content.
            old_lines = old_lines.replace(_TILDE_PH, '~')
            new_lines = new_lines.replace(_TILDE_PH, '~')
            # The ~~ technique uses raw Twine syntax in old_lines (the search pattern).
            # The HTML file stores these as &lt;&lt; &gt;&gt; so we must escape both sides.
            old_lines = escape_twine_tags(escape_html_between_tags(old_lines))
            new_lines = escape_twine_tags(escape_html_between_tags(new_lines))
            old_stripped = old_lines.strip()
            new_stripped = new_lines.strip()
            new_stripped = auto_escape_passage_bodies(new_stripped)

            # v0.6.0: Normalize through same pipeline as new-style entries
            # Store as (text, guards) tuple for uniform handling in patch_html_file
            empty_guards = {
                'if_exists':              [],
                'if_not_exists':          [],
                'if_reg_exists':          [],
                'if_reg_not_exists':      [],
                'if_mod_loaded':          [],
                'if_mod_not_loaded':      [],
                'if_passage_exists':      [],
                'if_passage_not_exists':  [],
                'if_function_exists':     [],
                'if_function_not_exists': [],
                'if_passage_contains':    [],
                'if_passage_has_tag':     [],
                'if_version_at_least':    [],
            }
            mod_dict[old_stripped] = (new_stripped, empty_guards)
            # v0.7.6: record insertion order in mod_list (preserves duplicates)
            mod_list.append((old_stripped, mod_file))

            # Track in key_to_mod for O(1) inner replacement cleanup
            if key_to_mod is not None:
                key_to_mod[old_stripped] = mod_file

            # Register conflict
            if conflict_map is not None:
                _register_conflict(conflict_map, old_stripped, mod_file, 'Replace (legacy ~~)')

            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(old_stripped)
            
# ------------------------------------------------
# Guard clause and ReplaceReg helpers
# ------------------------------------------------

# Matches any guard/condition line and captures the bracketed value.
_GUARD_RE = re.compile(
    r'(?m)^(?P<kind>IfExists|IfNotExists|IfRegExists|IfRegNotExists'
    r'|IfModLoaded|IfModNotLoaded|IfPassageExists|IfPassageNotExists'
    r'|IfFunctionExists|IfFunctionNotExists'
    r'|IfPassageContains|IfPassageHasTag|IfVersionAtLeast)\s*\[(?P<value>[^\]]*)\]:\s*$'
)

def _parse_guards(text):
    """
    Strip guard lines from *text* and return (cleaned_text, guards_dict).

    guards_dict keys: 'if_exists', 'if_not_exists', 'if_reg_exists', 'if_reg_not_exists'
    Each value is a list of strings (multiple guards of the same kind are allowed).
    """
    guards = {
        'if_exists':              [],
        'if_not_exists':          [],
        'if_reg_exists':          [],
        'if_reg_not_exists':      [],
        'if_mod_loaded':          [],
        'if_mod_not_loaded':      [],
        'if_passage_exists':      [],
        'if_passage_not_exists':  [],
        'if_function_exists':     [],
        'if_function_not_exists': [],
        'if_passage_contains':    [],
        'if_passage_has_tag':     [],
        'if_version_at_least':    [],
    }
    key_map = {
        'IfExists':             'if_exists',
        'IfNotExists':          'if_not_exists',
        'IfRegExists':          'if_reg_exists',
        'IfRegNotExists':       'if_reg_not_exists',
        'IfModLoaded':          'if_mod_loaded',
        'IfModNotLoaded':       'if_mod_not_loaded',
        'IfPassageExists':      'if_passage_exists',
        'IfPassageNotExists':   'if_passage_not_exists',
        'IfFunctionExists':     'if_function_exists',
        'IfFunctionNotExists':  'if_function_not_exists',
        'IfPassageContains':    'if_passage_contains',
        'IfPassageHasTag':      'if_passage_has_tag',
        'IfVersionAtLeast':     'if_version_at_least',
    }

    def _unescape_guard_value(v):
        # Only unescape bracket-syntax escapes used by guard parsing.
        # Keep regex escapes (e.g., \d, \s, \b) intact for IfReg* guards.
        out = []
        i = 0
        while i < len(v):
            if v[i] == '\\' and i + 1 < len(v) and v[i + 1] in (']', '\\'):
                out.append(v[i + 1])
                i += 2
                continue
            out.append(v[i])
            i += 1
        return ''.join(out)

    def collect(m):
        kind = m.group('kind')
        val = m.group('value')
        if kind in ('IfPassageContains', 'IfPassageHasTag'):
            val = _unescape_guard_value(val)
        guards[key_map[kind]].append(val)
        return ''

    cleaned = _GUARD_RE.sub(collect, text)
    return cleaned.strip(), guards


def _check_guards(guards, html_content, loaded_mod_files=None, passage_registry=None,
                  passage_dict=None, passage_meta=None, script_block=None):
    """
    Return True if all guards pass, False if any guard fails.
    Called at patch time against the live html_content.

    loaded_mod_files: optional set/list of mod filenames (basename only)
    currently loaded -- used by IfModLoaded / IfModNotLoaded guards.


    """
    for val in guards['if_exists']:
        # v0.7.0: normalize so modders can write <<macros>> or &lt;&lt;macros&gt;&gt;
        _norm = escape_twine_tags(val)
        if _norm not in html_content:
            return False
    for val in guards['if_not_exists']:
        _norm = escape_twine_tags(val)
        if _norm in html_content:
            return False
    for val in guards['if_reg_exists']:
        if not re.search(val, html_content, re.DOTALL):
            return False
    for val in guards['if_reg_not_exists']:
        if re.search(val, html_content, re.DOTALL):
            return False
    # ---- Mod-load guards (v0.5.3) ----
    if loaded_mod_files is not None:
        loaded_basenames = {os.path.basename(f).lower() for f in loaded_mod_files}
        for val in guards.get('if_mod_loaded', []):
            if val.lower() not in loaded_basenames:
                return False
        for val in guards.get('if_mod_not_loaded', []):
            if val.lower() in loaded_basenames:
                return False
    # ---- Passage-existence guards (v0.5.3+) ----
    # v0.7.2: use passage_dict for O(1) lookup when available.
    # Also checks passage_registry so passages added by earlier mods via
    # Add Passage directives are visible even before Phase 7 injection.
    _reg_names = {e['name'] for e in passage_registry} if passage_registry else set()
    for val in guards.get('if_passage_exists', []):
        if passage_dict is not None:
            if val not in passage_dict and val not in _reg_names:
                return False
        else:
            pat = r'<tw-passagedata[^>]*name="' + re.escape(val) + r'"'
            if not re.search(pat, html_content) and val not in _reg_names:
                return False
    for val in guards.get('if_passage_not_exists', []):
        if passage_dict is not None:
            if val in passage_dict or val in _reg_names:
                return False
        else:
            pat = r'<tw-passagedata[^>]*name="' + re.escape(val) + r'"'
            if re.search(pat, html_content) or val in _reg_names:
                return False
    # ---- Passage-content guards ----
    for val in guards.get('if_passage_contains', []):
        if '|' not in val:
            continue  # malformed, skip
        psg_name, search_text = val.split('|', 1)
        # v0.7.2: O(1) body lookup via passage_dict
        if passage_dict is not None:
            _pc_body = passage_dict.get(psg_name)
            if _pc_body is None:
                return False
            decoded_body = _pc_body.replace('&lt;', '<').replace('&gt;', '>')
            decoded_body = decoded_body.replace('&quot;', '"').replace('&amp;', '&')
            decoded_body = decoded_body.replace('&#39;', "'")
        else:
            psg_pat = _get_compiled(
                r'<tw-passagedata[^>]*name="' + re.escape(psg_name) + r'"[^>]*>(.*?)</tw-passagedata>',
                re.DOTALL
            )
            psg_m = psg_pat.search(html_content)
            if not psg_m:
                return False
            decoded_body = psg_m.group(1)
            decoded_body = decoded_body.replace('&lt;', '<').replace('&gt;', '>')
            decoded_body = decoded_body.replace('&quot;', '"').replace('&amp;', '&')
            decoded_body = decoded_body.replace('&#39;', "'")
        if search_text not in decoded_body:
            return False

    # ---- Passage-tag guards ----
    for val in guards.get('if_passage_has_tag', []):
        if '|' not in val:
            continue  # malformed, skip
        psg_name, tag_name = val.split('|', 1)
        # v0.7.2: O(1) open-tag lookup via passage_meta
        if passage_meta is not None and psg_name in passage_meta:
            _pm_open = passage_meta[psg_name][0]
            _tm = re.search(r'tags="([^"]*)', _pm_open)
            if not _tm or tag_name not in _tm.group(1).split():
                return False
        else:
            tag_pat = _get_compiled(
                r'<tw-passagedata[^>]*name="' + re.escape(psg_name) + r'"[^>]*tags="([^"]*)"'
            )
            tag_m = tag_pat.search(html_content)
            if not tag_m:
                return False
            if tag_name not in tag_m.group(1).split():
                return False

    # ---- IfVersionAtLeast guard (v0.7.1) ----
    # Reads the game version string from <tw-storydata creator-version="...">
    # and compares it against the required minimum.  Semver comparison: major,
    # minor, patch integers.  Missing patch treated as 0.
    for val in guards.get('if_version_at_least', []):
        def _parse_ver(s):
            parts = re.sub(r'[^0-9.]', '', s).split('.')
            try:
                return tuple(int(p) for p in (parts + ['0', '0', '0'])[:3])
            except ValueError:
                return (0, 0, 0)
        _ver_m = re.search(r'<tw-storydata[^>]+creator-version="([^"]+)"', html_content)
        _game_ver = _parse_ver(_ver_m.group(1)) if _ver_m else (0, 0, 0)
        _req_ver  = _parse_ver(val)
        if _game_ver < _req_ver:
            return False

    # ---- Function-existence guards (v0.5.3) ----
    # v0.7.2: search script_block (0.1MB) instead of html_content (20MB) when available.
    _func_search_target = script_block if script_block is not None else html_content
    for val in guards.get('if_function_exists', []):
        func_pat = _get_compiled(
            r'(?:^|[\s;])' + re.escape(val) + r'\s*[=:]\s*function'
            r'|function\s+' + re.escape(val) + r'\s*\(',
            re.MULTILINE
        )
        if not func_pat.search(_func_search_target):
            return False
    for val in guards.get('if_function_not_exists', []):
        func_pat = _get_compiled(
            r'(?:^|[\s;])' + re.escape(val) + r'\s*[=:]\s*function'
            r'|function\s+' + re.escape(val) + r'\s*\(',
            re.MULTILINE
        )
        if func_pat.search(html_content):
            return False
    return True


# Tokenises With{N}: headers inside a ReplaceReg block
_WITH_GROUP_RE = re.compile(r'(?m)^With\{(\d+)\}:\s*$')

def _parse_with_groups(text):
    """
    Split *text* on With{N}: header lines.
    Returns a list of (group_index, body_text) tuples in appearance order.
    Guard lines within each body are stripped.
    """
    tokens = list(_WITH_GROUP_RE.finditer(text))
    if not tokens:
        return []

    results = []
    for i, tok in enumerate(tokens):
        start = tok.end()
        end = tokens[i + 1].start() if i + 1 < len(tokens) else len(text)
        body, _ = _parse_guards(text[start:end])
        results.append((int(tok.group(1)), body.strip()))
    return results


#Function to Process Mod Files Using the New Technique (Replace:/With: and Add Passage:)
# ------------------------------------------------
# Helpers for new directive parsing
# ------------------------------------------------

# All directive tokens that mark the start of a new block at column 0.
_ALL_DIRECTIVE_TOKENS = [
    'Replace:', 'ReplaceReg [', 'Add Passage:', 'Add Javascript:',
    'Add CSS:', 'Add Events:', 'Add Function [', 'Add Variable [',
    'Append Array [',
    'Append Variable to Class [', 'Append Function to Class [',
    'Replace Function [', 'Replace Function Signature [',
    'Insert Before [', 'Insert After [',
    'Insert Into Function [',
    'Delete Block [', 'Rename Passage [', 'Hook [',
    'Insert Into Array [', 'Insert Into Object [',
    'Replace In Passage [', 'Delete Span [',
    'Prepend To Passage [', 'Append To Passage [',
    'Add Tag To Passage [', 'Remove Tag From Passage [',
    'Replace In Function [', 'Delete In Passage [', 'Move Passage [',
    # v0.7.1 new directives
    'Merge Into Object [', 'Clone Passage [', 'Wrap Passage [',
    'Replace In All Passages [', 'Add StoryVar [',
]

# ---- Guard hoist infrastructure ----
# Import from KittyDiffAssist when present (enables port draft generation).
# Falls back to inline definition so the patcher works standalone.
try:
    from KittyDiffAssist import (
        hoist_guards_to_with_bodies as _hoist_guards_to_with_bodies,
    )
    import KittyDiffAssist as _KittyDiffAssist
    _DIFFASSIST_AVAILABLE = True
except ImportError:
    _KittyDiffAssist = None
    _DIFFASSIST_AVAILABLE = False

if not _DIFFASSIST_AVAILABLE:
    _GUARD_LINE_RE = re.compile(
        r'^(?:IfExists|IfNotExists|IfRegExists|IfRegNotExists'
        r'|IfModLoaded|IfModNotLoaded|IfPassageExists|IfPassageNotExists'
        r'|IfFunctionExists|IfFunctionNotExists|IfPassageContains|IfPassageHasTag)'
        r'\s*\[(?:\\.|[^\]])*\]:\s*$'
    )
    
    # Directive tokens whose content comes after an anchor then With: -- guards must go after With:
    _HAS_ANCHOR_BEFORE_WITH = frozenset([
        'Insert Before [', 'Insert After [', 'Insert Into Function [',
        'Replace In Passage [', 'Replace In Function [',
        'Hook [', 'Prepend To Passage [', 'Append To Passage [',
    ])
    
    # All directive tokens -- kept in sync with patcher
    _ALL_DIRECTIVE_TOKENS = [
        'Replace:', 'ReplaceReg [', 'Add Passage:', 'Add Javascript:',
        'Add CSS:', 'Add Events:', 'Add Function [', 'Add Variable [',
        'Append Array [',
        'Append Variable to Class [', 'Append Function to Class [',
        'Replace Function [', 'Replace Function Signature [',
        'Insert Before [', 'Insert After [',
        'Insert Into Function [',
        'Delete Block [', 'Rename Passage [', 'Hook [',
        'Insert Into Array [', 'Insert Into Object [',
        'Replace In Passage [', 'Delete Span [',
        'Prepend To Passage [', 'Append To Passage [',
        'Add Tag To Passage [', 'Remove Tag From Passage [',
        'Replace In Function [', 'Delete In Passage [', 'Move Passage [',
    ]

if not _DIFFASSIST_AVAILABLE:
    
    def _hoist_guards_to_with_bodies(mod_content):
        """
        Move guard lines (IfPassageExists, IfFunctionExists, etc.) that immediately
        precede a directive token into the correct body region where _parse_guards
        will find and enforce them.
    
        - For Replace: and directives with anchor+With: (Insert After etc):
          guards are injected after the With: line.
        - For body-only directives (Add Function, Delete Block, Add Passage etc):
          guards are injected immediately after the directive token line.
        - Guards separated from their directive by blank lines only are still hoisted.
        - Guard lines NOT immediately followed by a directive are left in place.
        """
        lines = mod_content.splitlines(keepends=True)
        out = []
        i = 0
        while i < len(lines):
            s = lines[i].rstrip('\r\n')
            if not _GUARD_LINE_RE.match(s):
                out.append(lines[i])
                i += 1
                continue
    
            # Collect consecutive guard lines
            guard_buf = []
            while i < len(lines) and _GUARD_LINE_RE.match(lines[i].rstrip('\r\n')):
                guard_buf.append(lines[i])
                i += 1
    
            # Skip blank lines between guards and possible directive
            blank_buf = []
            while i < len(lines) and lines[i].strip() == '':
                blank_buf.append(lines[i])
                i += 1
    
            if i >= len(lines):
                out.extend(guard_buf)
                out.extend(blank_buf)
                continue
    
            directive_s = lines[i].rstrip('\r\n')
            if not any(directive_s == tok or directive_s.startswith(tok)
                       for tok in _ALL_DIRECTIVE_TOKENS):
                # Not a directive -- leave guards in place unchanged
                out.extend(guard_buf)
                out.extend(blank_buf)
                continue
    
            # Guards immediately precede a directive. Suppress blank lines between them.
            out.append(lines[i])  # directive token line
            i += 1
    
            needs_with_scan = (
                directive_s == 'Replace:'
                or any(directive_s == tok or directive_s.startswith(tok)
                       for tok in _HAS_ANCHOR_BEFORE_WITH)
            )
    
            if needs_with_scan:
                # Scan forward for With: line, append guards after it
                found_with = False
                while i < len(lines):
                    out.append(lines[i])
                    if lines[i].strip() == 'With:':
                        out.extend(guard_buf)
                        found_with = True
                        i += 1
                        break
                    i += 1
                if not found_with:
                    out.extend(guard_buf)
            else:
                # Body-only directive: inject guards immediately after the token line
                out.extend(guard_buf)
    
        return ''.join(out)
    
    
    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    

def _find_next_directive(text):
    """Return the start index of the next top-level directive in text, or len(text)."""
    best = len(text)
    for tok in _ALL_DIRECTIVE_TOKENS:
        m = re.search(r'(?m)^' + re.escape(tok), text)
        if m and m.start() < best:
            best = m.start()
    return best

def _is_in_script_block(html, position):
    """Return True if position is inside the <script> block (before </script><tw-passagedata).

    Mirrors C# PatchEngine.IsInsideScriptBlock. The script block ends at the
    '</script><tw-passagedata' boundary -- everything before it is raw JS,
    everything after is passage content.  Used by Insert After/Before to
    decide whether a body needs EscapeTwineTags encoding before injection.
    """
    script_end = html.find('</script><tw-passagedata')
    return script_end < 0 or position < script_end

def _register_conflict(conflict_map, target_name, mod_file, kind):
    """Record that mod_file touches target_name with the given directive kind."""
    key = target_name.strip()
    if key not in conflict_map:
        conflict_map[key] = []
    conflict_map[key].append((mod_file, kind))


def _split_multi_passage_with_body(old_lines, new_line_stripped, mod_file, mod_file_indexes, handle_output_fn, passage_registry=None, passage_names_seen=None):
    """
    Detect and split a Replace: With: body that contains multiple <tw-passagedata> blocks.

    v0.6.0: Routes extra passages into passage_registry instead of the
    </tw-storydata> accumulator.  Eliminates the last consumer of the
    accumulator pattern for passages.

    Returns (cleaned_with_body, extra_count).
    """
    # Fast path: no multi-passage content
    if new_line_stripped.count('<tw-passagedata') <= 1:
        return new_line_stripped, 0

    target_name_m = re.search(r'<tw-passagedata[^>]*name="([^"]+)"', old_lines)
    target_name = target_name_m.group(1) if target_name_m else None

    passage_blocks = re.split(r'(?=<tw-passagedata)', new_line_stripped)

    target_block = None
    extra_blocks = []

    for block in passage_blocks:
        block = block.strip()
        if not block:
            continue
        if not block.startswith('<tw-passagedata'):
            if target_block is None:
                target_block = (target_block or '') + block
            continue
        name_m = re.search(r'<tw-passagedata[^>]*name="([^"]+)"', block)
        block_name = name_m.group(1) if name_m else None
        if block_name == target_name or target_block is None:
            target_block = block
        else:
            if '</tw-passagedata>' in block:
                extra_blocks.append((block_name, block))

    if not extra_blocks:
        return new_line_stripped, 0

    # Route extra passages into passage_registry
    if passage_registry is not None:
        for block_name, block in extra_blocks:
            block = re.sub(r'(<tw-passagedata[^>]*)pid="[^"]*"', r'\1pid="auto"', block, count=1)
            if not block.rstrip().endswith('</tw-passagedata>'):
                block = block.rstrip() + '\n</tw-passagedata>'

            body_m = re.search(r'<tw-passagedata[^>]*>(.*?)</tw-passagedata>', block, re.DOTALL)
            body = body_m.group(1).strip() if body_m else ''
            tags_m = re.search(r'tags="([^"]*)"', block)
            tags = tags_m.group(1) if tags_m else ''

            record = {
                'name':     block_name,
                'tags':     tags,
                'pid':      'auto',
                'body':     body,
                'guards':   {'if_exists': [], 'if_not_exists': [], 'if_reg_exists': [], 'if_reg_not_exists': []},
                'mod_file': mod_file,
                'format':   'full',
            }

            if passage_names_seen is not None and block_name in passage_names_seen:
                first_idx = passage_names_seen[block_name]
                first_mod = passage_registry[first_idx]['mod_file']
                handle_output_fn(
                    f"DUPLICATE PASSAGE '{block_name}': already defined by {first_mod}, "
                    f"skipping copy from {mod_file} (multi-passage split).",
                    "alllogs"
                )
            else:
                if passage_names_seen is not None:
                    passage_names_seen[block_name] = len(passage_registry)
                passage_registry.append(record)

            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            label = f'Add Passage: [{block_name}] (auto-split from multi-passage Replace:)'
            mod_file_indexes[mod_file].append(label)

    handle_output_fn(
        f"MULTI-PASSAGE REPLACE: With: body contained {len(extra_blocks) + 1} passages. "
        f"Auto-split: \'{target_name}\' stays as Replace:, "
        f"{len(extra_blocks)} extra passage(s) routed to passage registry. "
        f"Consider restructuring this mod to use separate Add Passage: blocks.",
        "alllogs"
    )

    return target_block if target_block else new_line_stripped, len(extra_blocks)


# ------------------------------------------------
# Registry extractors (v0.6.0)
# ------------------------------------------------

def _extract_add_passages(mod_content, passage_registry, passage_names_seen, mod_file, mod_file_indexes):
    """
    Extract all Add Passage: blocks (full and shorthand format) from mod_content.
    Appends parsed records to passage_registry, tracks names in passage_names_seen.
    Returns mod_content with all Add Passage: blocks removed.
    """
    extracted_ranges = []  # (start, end) pairs to remove from mod_content

    # ---- Full format: Add Passage:\n<tw-passagedata ...>body</tw-passagedata> ----
    # Matches the entire block from Add Passage: through the LAST </tw-passagedata>
    # to handle multi-passage blocks (e.g. B&F chains 108 passages under one directive).
    full_pat = _get_compiled(
        r'^Add Passage:\s*\n'
        r'((?:<tw-passagedata[^>]*>.*?</tw-passagedata>\s*)+)',
        re.MULTILINE | re.DOTALL
    )
    for m in full_pat.finditer(mod_content):
        block = m.group(1)
        # Split into individual passages
        passage_pat = _get_compiled(
            r'(<tw-passagedata[^>]*>)(.*?)(</tw-passagedata>)',
            re.DOTALL
        )
        passage_count = 0
        for pm in passage_pat.finditer(block):
            open_tag = pm.group(1)
            body = pm.group(2).strip()
            name_m = re.search(r'name="([^"]+)"', open_tag)
            if not name_m:
                handle_output(
                    f"Add Passage: skipped malformed block (missing name attribute) in {mod_file}",
                    "alllogs"
                )
                continue
            name = name_m.group(1)
            if not body:
                handle_output(
                    f"Add Passage: skipped '{name}' -- empty body in {mod_file}",
                    "alllogs"
                )
                continue
            tags_m = re.search(r'tags="([^"]*)"', open_tag)
            tags = tags_m.group(1) if tags_m else ''

            # Parse guards from the body
            body, guards = _parse_guards(body)

            record = {
                'name':     name,
                'tags':     tags,
                'pid':      'auto',
                'body':     body.strip(),
                'guards':   guards,
                'mod_file': mod_file,
                'format':   'full',
            }

            if name in passage_names_seen:
                first_idx = passage_names_seen[name]
                first_mod = passage_registry[first_idx]['mod_file']
                handle_output(
                    f"DUPLICATE PASSAGE '{name}': already defined by {first_mod}, "
                    f"skipping copy from {mod_file}.",
                    "alllogs"
                )
                handle_output(
                    f"DUPLICATE PASSAGE '{name}': already defined by {first_mod}, "
                    f"skipping copy from {mod_file}.",
                    "failed"
                )
            else:
                passage_names_seen[name] = len(passage_registry)
                passage_registry.append(record)

            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(f'Add Passage: [{name}]')
            passage_count += 1

        extracted_ranges.append((m.start(), m.end()))

    # ---- Shorthand format: Add Passage: Name\ntags: ...\nbody ----
    shorthand_pat = _get_compiled(r'^Add Passage:[^\S\n]+(\S.+?)\s*$', re.MULTILINE)
    for m in shorthand_pat.finditer(mod_content):
        # Skip if this range overlaps with an already-extracted full-format block
        if any(s <= m.start() < e for s, e in extracted_ranges):
            continue
        pname = m.group(1).strip()
        rest_start = m.end() + 1 if m.end() < len(mod_content) and mod_content[m.end()] == '\n' else m.end()
        rest = mod_content[rest_start:]
        # Check for optional tags: line
        tags = ''
        tags_m_sh = re.match(r'tags:\s*(.*?)\s*\n', rest)
        if tags_m_sh:
            tags = tags_m_sh.group(1).strip()
            body_start = rest_start + tags_m_sh.end()
        else:
            body_start = rest_start
        # Find where the body ends using the standard directive boundary detector
        body_rest = mod_content[body_start:]
        body_end_offset = _find_next_directive(body_rest)
        body = body_rest[:body_end_offset].strip()

        if not pname:
            handle_output(
                f"Add Passage: skipped malformed shorthand block (empty name) in {mod_file}",
                "alllogs"
            )
            extracted_ranges.append((m.start(), body_start + body_end_offset))
            continue
        if not body:
            handle_output(
                f"Add Passage: skipped '{pname}' -- empty body in {mod_file}",
                "alllogs"
            )
            extracted_ranges.append((m.start(), body_start + body_end_offset))
            continue

        # Parse guards from the body
        body, guards = _parse_guards(body)

        record = {
            'name':     pname,
            'tags':     tags,
            'pid':      'auto',
            'body':     body.strip(),
            'guards':   guards,
            'mod_file': mod_file,
            'format':   'shorthand',
        }

        if pname in passage_names_seen:
            first_idx = passage_names_seen[pname]
            first_mod = passage_registry[first_idx]['mod_file']
            handle_output(
                f"DUPLICATE PASSAGE '{pname}': already defined by {first_mod}, "
                f"skipping copy from {mod_file}.",
                "alllogs"
            )
            handle_output(
                f"DUPLICATE PASSAGE '{pname}': already defined by {first_mod}, "
                f"skipping copy from {mod_file}.",
                "failed"
            )
        else:
            passage_names_seen[pname] = len(passage_registry)
            passage_registry.append(record)

        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Add Passage: [{pname}]')

        extracted_ranges.append((m.start(), body_start + body_end_offset))

    # Remove extracted blocks from mod_content (reverse order to preserve offsets)
    extracted_ranges.sort(key=lambda r: r[0], reverse=True)
    for start, end in extracted_ranges:
        mod_content = mod_content[:start] + mod_content[end:]

    return mod_content


def _extract_add_js_css_events(mod_content, js_registry, css_registry, events_registry, mod_file, mod_file_indexes):
    """
    Extract Add Javascript:, Add CSS:, and Add Events: blocks from mod_content.
    Appends parsed records to the appropriate registry.
    Returns mod_content with all extracted blocks removed.
    """
    directives = [
        ('Add Javascript:', js_registry),
        ('Add CSS:',         css_registry),
        ('Add Events:',      events_registry),
    ]
    extracted_ranges = []

    # Build terminator from ALL known directive tokens so an Add Events: body
    # is correctly terminated by Insert After, Add Function, etc. -- not just
    # by the three registry directives and Replace:/~~.
    _terminator_alts = '|'.join(re.escape(tok) for tok in _ALL_DIRECTIVE_TOKENS)

    for directive_token, registry in directives:
        pat = _get_compiled(
            r'^' + re.escape(directive_token) + r'\s*\n'
            r'(?P<content>.*?)(?='
            r'^(?:' + _terminator_alts + r'|~~|\Z))',
            re.MULTILINE | re.DOTALL
        )
        for m in pat.finditer(mod_content):
            # Skip if this range overlaps with an already-extracted block
            if any(s <= m.start() < e for s, e in extracted_ranges):
                continue
            body = m.group('content').strip()
            if not body:
                continue
            body, guards = _parse_guards(body)
            body = body.strip()
            if not body:
                continue
            record = {
                'body':     body,
                'guards':   guards,
                'mod_file': mod_file,
            }
            registry.append(record)
            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(f'{directive_token} block')
            extracted_ranges.append((m.start(), m.end()))

    # Remove extracted blocks from mod_content (reverse order)
    extracted_ranges.sort(key=lambda r: r[0], reverse=True)
    for start, end in extracted_ranges:
        mod_content = mod_content[:start] + mod_content[end:]

    return mod_content


def proc_replacement_new(mod_content, mod_dict, mod_list, mod_file_indexes, mod_file, mod_reg_list, mod_struct_list, mod_func_list, mod_hook_list, conflict_map, passage_registry, passage_names_seen, js_registry, css_registry, events_registry, key_to_mod):
    # Hoist guard lines that precede directives into the correct body region
    # so that _parse_guards enforces them for every directive type uniformly.
    mod_content = _hoist_guards_to_with_bodies(mod_content)

    # ---- v0.6.0: Registry extraction phase ----
    # Extract Add Passage, Add Javascript, Add CSS, Add Events blocks into
    # their respective registries BEFORE pre_proc runs.  This replaces the
    # old shortcut-to-Replace/With conversion entirely.
    mod_content = _extract_add_passages(
        mod_content, passage_registry, passage_names_seen,
        mod_file, mod_file_indexes
    )
    mod_content = _extract_add_js_css_events(
        mod_content, js_registry, css_registry, events_registry,
        mod_file, mod_file_indexes
    )


    # Targets whose content must NOT be escape_twine_tag'd (raw JS/CSS injected into script/style blocks)
    raw_targets = {"</script><tw-passagedata", "</style><script", "setup.Events.db =\n["}


    # ---- Classic Replace: blocks ----
    # Use a stateful line scanner so a bare "Replace:" inside a With: body is treated
    # as literal content, not a new directive boundary.
    _IDLE, _IN_REPLACE, _IN_WITH = 0, 1, 2

    def _split_replace_blocks(text):
        state = _IDLE
        old_buf, with_buf = [], []
        for line in text.splitlines(keepends=True):
            s = line.rstrip('\r\n')
            if state == _IDLE:
                if s.strip() == 'Replace:':
                    state = _IN_REPLACE
                    old_buf, with_buf = [], []
            elif state == _IN_REPLACE:
                if s.strip() == 'With:':
                    state = _IN_WITH
                else:
                    old_buf.append(line)
            else:  # _IN_WITH
                # Terminate the With: body on Replace: or ~~ (existing behavior),
                # but ALSO terminate on any other directive token.  This prevents
                # Insert After/Before/Replace Function blocks that immediately follow
                # a Replace: block from being absorbed into that block's With: body
                # and injected as literal text into the HTML.
                _ABSORBED_DIRECTIVE = any(
                    s.strip() == tok or s.strip().startswith(tok)
                    for tok in _ALL_DIRECTIVE_TOKENS
                    if tok not in ('With:', '~~', 'Replace:')
                )
                if s.strip() == 'Replace:' and old_buf:
                    yield (''.join(old_buf), ''.join(with_buf))
                    state = _IN_REPLACE
                    old_buf, with_buf = [], []
                elif s.strip() == '~~' and old_buf:
                    yield (''.join(old_buf), ''.join(with_buf))
                    state = _IDLE
                    old_buf, with_buf = [], []
                elif _ABSORBED_DIRECTIVE and old_buf:
                    yield (''.join(old_buf), ''.join(with_buf))
                    # Don't consume this line -- let it be parsed by the IA/IB/RF path
                    # by falling back to IDLE so the outer parsers see it in mod_content
                    state = _IDLE
                    old_buf, with_buf = [], []
                else:
                    with_buf.append(line)
        if state == _IN_WITH and old_buf:
            yield (''.join(old_buf), ''.join(with_buf))

    for old_lines, new_lines in _split_replace_blocks(mod_content):
        old_lines = escape_html_between_tags(old_lines)
        new_lines = escape_html_between_tags(new_lines)

        old_line_stripped = old_lines.strip()

        # Strip guard clauses from the With: body before further processing
        new_lines, guards = _parse_guards(new_lines)

        # Raw targets (script/style blocks) must stay as raw JS -- do not escape.
        # All other targets: escape << >> in the With: body so Twine macros survive
        # round-tripping through the HTML file's escaped passage content.
        if old_line_stripped in raw_targets:
            new_line_stripped = new_lines.strip()
        else:
            new_lines = escape_twine_tags(new_lines)
            new_line_stripped = new_lines.strip()
            new_line_stripped = auto_escape_passage_bodies(new_line_stripped)

        # Multi-passage split: if With: body contains multiple passages, extract
        # extra ones into Add Passage: accumulator and keep only the target passage.
        # Only applies to non-raw targets (passage replacements, not script blocks).
        if old_line_stripped not in raw_targets:
            new_line_stripped, _extra = _split_multi_passage_with_body(
                old_lines, new_line_stripped, mod_file, mod_file_indexes, handle_output,
                passage_registry=passage_registry, passage_names_seen=passage_names_seen
            )

        # v0.6.0: No more accumulator pattern -- all entries go as (text, guards) tuples
        mod_dict[old_line_stripped] = (new_line_stripped, guards)
        # v0.7.6: record insertion order in mod_list (preserves duplicates)
        mod_list.append((old_line_stripped, mod_file))
        if old_line_stripped not in raw_targets:
            _register_conflict(conflict_map, old_line_stripped, mod_file, 'Replace')

        # Part C (v0.6.0): track which mod owns each mod_dict key
        key_to_mod[old_line_stripped] = mod_file

        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        if old_lines not in mod_file_indexes:
            mod_file_indexes[old_lines] = []
        mod_file_indexes[mod_file].append(old_line_stripped)

    # ---- Multi-pass: absorb inner replacements into With: bodies (v0.6.0 optimized) ----
    # A Replace: block whose target exists inside another block's With: body (rather than
    # the game HTML) is an inner replacement.  Apply it directly into the host body and
    # remove it from mod_dict so it doesn't produce a spurious "No match found" at patch time.
    #
    # v0.6.0: Build a reverse content index (inner_candidates) mapping each search_key
    # to the set of host_keys whose With body contains that key.  This replaces the
    # O(D^2) nested loop with targeted candidate lookups.
    #
    # Escaping rules:
    #   - Non-raw host bodies have been through escape_twine_tags, so search using the
    #     escaped form of the key and inject the already-escaped replacement as-is.
    #   - Raw host bodies (script/style) are unescaped JS, so search using the raw key
    #     and unescape the replacement before injecting.
    this_mod_keys = list(mod_file_indexes.get(mod_file, []))
    all_inner_keys = []
    MAX_INNER_PASSES = 20

    # Build inner_candidates index: search_key -> set of host_keys containing it
    inner_candidates = {}
    active_keys_set = set(k for k in this_mod_keys if k in mod_dict)

    for search_key in active_keys_set:
        escaped_key = escape_twine_tags(search_key)
        candidates = set()
        for host_key in active_keys_set:
            if host_key == search_key or host_key not in mod_dict:
                continue
            host_entry = mod_dict[host_key]
            host_body = host_entry[0]
            host_is_raw = host_key in raw_targets
            actual_search = search_key if host_is_raw else escaped_key
            if actual_search in host_body:
                candidates.add(host_key)
        if candidates:
            inner_candidates[search_key] = candidates

    for _pass in range(MAX_INNER_PASSES):
        inner_keys = []

        for search_key in list(inner_candidates.keys()):
            if search_key not in mod_dict or search_key in all_inner_keys:
                continue
            host_keys = inner_candidates.get(search_key, set())
            search_entry = mod_dict[search_key]
            search_new = search_entry[0]
            escaped_key = escape_twine_tags(search_key)

            for host_key in list(host_keys):
                if host_key == search_key or host_key not in mod_dict:
                    continue
                host_entry = mod_dict[host_key]
                host_body = host_entry[0]
                host_is_raw = host_key in raw_targets

                actual_search = search_key if host_is_raw else escaped_key
                inject_new = search_new.replace('&lt;&lt;', '<<').replace('&gt;&gt;', '>>').replace('&gt;', '>').replace('&lt;', '<').replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'") if host_is_raw else search_new

                if actual_search in host_body:
                    new_body = host_body.replace(actual_search, inject_new, 1)
                    mod_dict[host_key] = (new_body, host_entry[1])
                    inner_keys.append(search_key)
                    # Part C (v0.6.0): use key_to_mod for O(1) cleanup
                    source_mod = key_to_mod.get(search_key)
                    if source_mod and source_mod in mod_file_indexes and search_key in mod_file_indexes[source_mod]:
                        mod_file_indexes[source_mod].remove(search_key)
                    # Update inner_candidates: the host body changed, so re-check
                    # if any remaining search_keys now match the new host body
                    for other_key in list(inner_candidates.keys()):
                        if other_key != search_key and other_key not in all_inner_keys:
                            ek = escape_twine_tags(other_key)
                            ak = other_key if host_is_raw else ek
                            if ak in new_body:
                                inner_candidates.setdefault(other_key, set()).add(host_key)
                    break

        if not inner_keys:
            break  # fixed point reached -- no more inner replacements found

        all_inner_keys.extend(inner_keys)
        for k in inner_keys:
            mod_dict.pop(k, None)
            inner_candidates.pop(k, None)

    # ---- ReplaceReg [pattern]: blocks ----
    # Split on the ReplaceReg [ token; first chunk is pre-amble (discard)
    reg_chunks = re.split(r'(?m)^ReplaceReg \[', mod_content)
    for chunk in reg_chunks[1:]:
        # chunk starts immediately after "ReplaceReg [", extract up to "]:"
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        pattern_str = chunk[:bracket_end]
        rest = chunk[bracket_end + 2:]  # everything after "]:"

        # A comment marker "#" may follow on the same line -- strip to next newline
        first_nl = rest.find('\n')
        rest = rest[first_nl + 1:] if first_nl != -1 else ''

        # Parse top-level guards and With{N}: groups
        rest, top_guards = _parse_guards(rest)
        group_entries = _parse_with_groups(rest)

        if not group_entries:
            continue

        mod_reg_list.append({
            'pattern': pattern_str,
            'groups':  group_entries,   # list of (group_index, replacement_text)
            'guards':  top_guards,
            'mod_file': mod_file,
        })

        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'ReplaceReg [{pattern_str}]')

    # ---- Append Array / Append Variable to Class / Append Function to Class /
    # ---- Insert Into Array / Insert Into Object blocks ----
    _STRUCT_KINDS = [
        ('Append Array [',              'append_array'),
        ('Append Variable to Class [',  'append_var'),
        ('Append Function to Class [',  'append_func'),
        ('Insert Into Array [',         'insert_into_array'),
        ('Insert Into Object [',        'insert_into_object'),
        ('Merge Into Object [',         'merge_into_object'),  # v0.7.1: deep merge
    ]
    for (token, kind) in _STRUCT_KINDS:
        chunks = re.split(r'(?m)^' + re.escape(token), mod_content)
        for chunk in chunks[1:]:
            bracket_end = chunk.find(']:')
            if bracket_end == -1:
                continue
            name_raw = chunk[:bracket_end].strip()
            # Optional scoping: "arrayName In Function [funcName]"
            scope_func = None
            scope_m = re.match(r'^(.+?)\s+In Function \[(.+?)\]$', name_raw)
            if scope_m:
                name_raw   = scope_m.group(1).strip()
                scope_func = scope_m.group(2).strip()
            name = name_raw
            rest = chunk[bracket_end + 2:]
            # Strip optional same-line comment and leading blank line
            first_nl = rest.find('\n')
            rest = rest[first_nl + 1:] if first_nl != -1 else ''
            # v0.7.5 fix: terminate body at ANY next top-level directive, not just
            # other struct-kind tokens.  The old loop only checked _STRUCT_KINDS,
            # so directives like Append To Passage, Add Function, Hook, etc. that
            # appeared after an Insert Into Object body were silently absorbed into
            # the object content and injected verbatim into the JS script block.
            next_directive = _find_next_directive(rest)
            body = rest[:next_directive].strip()
            if not body:
                continue
            body, guards = _parse_guards(body)
            mod_struct_list.append({
                'kind':       kind,
                'name':       name,
                'scope_func': scope_func,
                'content':    body,
                'guards':     guards,
                'mod_file':   mod_file,
            })
            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(f'{token}{name}]')
            
    # ---- Replace Function [name]: blocks ----
    # Replaces an entire named function body in the JS.
    rf_chunks = re.split(r'(?m)^Replace Function \[', mod_content)
    for chunk in rf_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        rest = rest[first_nl + 1:] if first_nl != -1 else ''
        # Terminate at next top-level directive
        _next = _find_next_directive(rest)
        body = rest[:_next].strip()
        if not body:
            continue
        body, guards = _parse_guards(body)
        entry = {'kind': 'replace_func', 'name': name, 'body': body, 'guards': guards, 'mod_file': mod_file}
        mod_func_list.append(entry)
        _register_conflict(conflict_map, name, mod_file, 'Replace Function')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Replace Function [{name}]')

    # ---- Insert Before [target]: / Insert After [target]: blocks ----
    for insert_kind, token in [('insert_before', 'Insert Before ['), ('insert_after', 'Insert After [')]:
        ia_chunks = re.split(r'(?m)^' + re.escape(token), mod_content)
        for chunk in ia_chunks[1:]:
            bracket_end = chunk.find(']:')
            if bracket_end == -1:
                continue
            name_raw = chunk[:bracket_end].strip()
            # v0.7.1: parse [ONCE], [soft], [typeof:funcName] modifiers from the anchor name
            _once   = '[ONCE]' in name_raw
            _soft   = '[soft]' in name_raw
            _typeof_m = re.search(r'\[typeof:([^\]]+)\]', name_raw)
            _typeof_func = _typeof_m.group(1).strip() if _typeof_m else None
            name = re.sub(r'\s*\[(ONCE|soft|typeof:[^\]]*)\]', '', name_raw).strip()
            rest = chunk[bracket_end + 2:]
            # Expect "With:" on the next non-empty line
            with_m = re.search(r'(?m)^With:\s*$', rest)
            if not with_m:
                continue
            rest_after = rest[with_m.end():]
            _next = _find_next_directive(rest_after)
            body = rest_after[:_next].strip()
            if not body:
                continue
            body, guards = _parse_guards(body)
            # v0.7.1: [typeof:funcName] wraps the injection in a typeof guard
            if _typeof_func:
                body = (
                    f'<<if typeof {_typeof_func} === "function">>\n'
                    f'{body}\n'
                    f'<</if>>'
                )
            entry = {
                'kind': insert_kind, 'name': name, 'body': body,
                'guards': guards, 'mod_file': mod_file,
                'once': _once, 'soft': _soft,
            }
            mod_func_list.append(entry)
            _register_conflict(conflict_map, name, mod_file, token.rstrip('[').strip())
            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(f'{token}{name}]')

    # ---- Delete Block [name]: blocks ----
    db_chunks = re.split(r'(?m)^Delete Block \[', mod_content)
    for chunk in db_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        guard_text = rest[:first_nl] if first_nl != -1 else rest
        _, guards = _parse_guards(guard_text)
        entry = {'kind': 'delete_block', 'name': name, 'guards': guards, 'mod_file': mod_file}
        mod_func_list.append(entry)
        _register_conflict(conflict_map, name, mod_file, 'Delete Block')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Delete Block [{name}]')

    # ---- Replace In Passage [PassageName]: blocks ----
    # Scoped replacement that searches only within the named passage body.
    # Format mirrors Insert After: anchor text on the line(s) after ]:\n,
    # then With:\n, then the replacement body.
    # The anchor only needs to be unique within that passage, not the whole HTML.
    # Falls back to a full-HTML Replace: if the passage is not found.
    # Tier 4 -- same porting cost as Replace: but scope-isolated to one passage.
    rip_chunks = re.split(r'(?m)^Replace In Passage \[', mod_content)
    for chunk in rip_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        passage_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        # Expect "With:" somewhere after the anchor text (same as Insert After)
        with_m = re.search(r'(?m)^With:\s*$', rest)
        if not with_m:
            continue
        # anchor = everything between ]: and With:
        anchor_raw = rest[:with_m.start()].strip()
        if not anchor_raw:
            continue
        # body = everything after With: up to next top-level directive
        rest_after = rest[with_m.end():]
        _next = _find_next_directive(rest_after)
        body_raw = rest_after[:_next].strip()
        # Encode anchor and body exactly as Replace: does for passage targets
        anchor_e = escape_twine_tags(escape_html_between_tags(anchor_raw))
        body_e   = escape_twine_tags(escape_html_between_tags(body_raw))
        body_e   = auto_escape_passage_bodies(body_e)
        body_e   = body_e.strip()
        body_e, guards = _parse_guards(body_e)
        entry = {
            'kind':         'replace_in_passage',
            'passage_name': passage_name,
            'name':         anchor_e,
            'body':         body_e,
            'guards':       guards,
            'mod_file':     mod_file,
        }
        mod_func_list.append(entry)
        label = f'Replace In Passage [{passage_name}]: {anchor_e[:40]}'
        _register_conflict(conflict_map, label, mod_file, 'Replace In Passage')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Delete Span [start] To [end]: blocks ----
    # Deletes everything from start_anchor through end_anchor (inclusive).
    # No With: body -- this directive only removes content.
    # The two anchors must both be present and start must precede end.
    # Tier 4 usage but preferable to Replace: for pure deletion -- no body drift.
    ds_chunks = re.split(r'(?m)^Delete Span \[', mod_content)
    for chunk in ds_chunks[1:]:
        # Format: Delete Span [start_anchor] To [end_anchor]:
        # Find the closing ] of the start anchor
        start_bracket_end = chunk.find(']')
        if start_bracket_end == -1:
            continue
        start_anchor = chunk[:start_bracket_end].strip()
        rest_after_start = chunk[start_bracket_end + 1:].lstrip()
        # Expect " To [end_anchor]:"
        if not rest_after_start.startswith('To ['):
            continue
        rest_after_to = rest_after_start[len('To ['):]
        end_bracket_end = rest_after_to.find(']:')
        if end_bracket_end == -1:
            continue
        end_anchor = rest_after_to[:end_bracket_end].strip()
        if not start_anchor or not end_anchor:
            continue
        # Encode both anchors the same way as Replace: targets
        start_enc = escape_twine_tags(escape_html_between_tags(start_anchor))
        end_enc   = escape_twine_tags(escape_html_between_tags(end_anchor))
        # Extract guards from any trailing text after the ]:\n line
        rest_after_end = rest_after_to[end_bracket_end + 2:]
        first_nl_ds = rest_after_end.find('\n')
        guard_text_ds = rest_after_end[:first_nl_ds] if first_nl_ds != -1 else rest_after_end
        _, guards = _parse_guards(guard_text_ds)
        entry = {
            'kind':         'delete_span',
            'name':         start_enc,
            'end_anchor':   end_enc,
            'guards':       guards,
            'mod_file':     mod_file,
        }
        mod_func_list.append(entry)
        label = f'Delete Span [{start_anchor[:40]}] To [{end_anchor[:40]}]'
        _register_conflict(conflict_map, label, mod_file, 'Delete Span')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Prepend To Passage [name]: / Append To Passage [name]: blocks ----
    # Injects the With: body at the very start (Prepend) or very end (Append) of a
    # named passage body.  Anchor is the passage name only -- Tier 2 resilience,
    # same as Hook [name]: and Insert After [anchor]:.
    # Safer than Insert Before/After when the passage's first/last line drifts
    # across game versions (e.g. StoryInit, PassageFooter, any passage whose
    # opening <<set>> block changes frequently).
    for insert_kind, token in [('prepend_to_passage', 'Prepend To Passage ['),
                                ('append_to_passage',  'Append To Passage [')]:
        pt_chunks = re.split(r'(?m)^' + re.escape(token), mod_content)
        for chunk in pt_chunks[1:]:
            bracket_end = chunk.find(']:')
            if bracket_end == -1:
                continue
            passage_name = chunk[:bracket_end].strip()
            rest = chunk[bracket_end + 2:]
            with_m = re.search(r'(?m)^With:\s*$', rest)
            if not with_m:
                continue
            rest_after = rest[with_m.end():]
            _next = _find_next_directive(rest_after)
            body_raw = rest_after[:_next].strip()
            if not body_raw:
                continue
            body_e = escape_twine_tags(escape_html_between_tags(body_raw))
            body_e = auto_escape_passage_bodies(body_e.strip())
            body_e, guards = _parse_guards(body_e)
            entry = {
                'kind':         insert_kind,
                'passage_name': passage_name,
                'name':         passage_name,   # used for conflict key
                'body':         body_e,
                'guards':       guards,
                'mod_file':     mod_file,
            }
            mod_func_list.append(entry)
            label = f'{token}{passage_name}]'
            _register_conflict(conflict_map, label, mod_file, token.rstrip('[').strip())
            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(label)

    # ---- Add Tag To Passage [name]: / Remove Tag From Passage [name]: blocks ----
    # Modifies the tags="..." attribute of a named passage's <tw-passagedata> opening tag.
    # Add Tag appends new space-separated tags; Remove Tag strips a specific tag.
    # Tier S: anchors on passage name only -- same resilience as Delete Block [name]:.
    # Eliminates the Replace: pattern of targeting 'name="X" tags="Y"' which breaks
    # whenever the dev adds or reorders tags on that passage.
    for tag_kind, token in [('add_tag_to_passage',    'Add Tag To Passage ['),
                             ('remove_tag_from_passage', 'Remove Tag From Passage [')]:
        tt_chunks = re.split(r'(?m)^' + re.escape(token), mod_content)
        for chunk in tt_chunks[1:]:
            bracket_end = chunk.find(']:')
            if bracket_end == -1:
                continue
            passage_name = chunk[:bracket_end].strip()
            rest = chunk[bracket_end + 2:]
            # Tags are on the next non-empty line (no With: needed)
            first_nl = rest.find('\n')
            tag_line = rest[:first_nl].strip() if first_nl != -1 else rest.strip()
            if not tag_line:
                continue
            # Guards may have been hoisted into tag_line by _hoist_guards_to_with_bodies
            tag_text, guards = _parse_guards(tag_line)
            tag_text = tag_text.strip()
            if not tag_text:
                continue
            entry = {
                'kind':         tag_kind,
                'passage_name': passage_name,
                'name':         passage_name,
                'tags':         tag_text,
                'guards':       guards,
                'mod_file':     mod_file,
            }
            mod_func_list.append(entry)
            label = f'{token}{passage_name}]: {tag_text[:40]}'
            _register_conflict(conflict_map, label, mod_file, token.rstrip('[').strip())
            if mod_file not in mod_file_indexes:
                mod_file_indexes[mod_file] = []
            mod_file_indexes[mod_file].append(label)
    hook_chunks = re.split(r'(?m)^Hook \[', mod_content)
    for chunk in hook_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        rest = rest[first_nl + 1:] if first_nl != -1 else ''
        # Expect "before:", "after:", or "around:" header
        timing_m = re.search(r'(?m)^(before|after|around):\s*$', rest)
        if not timing_m:
            continue
        timing = timing_m.group(1)
        hook_body = rest[timing_m.end():].strip()
        _next = _find_next_directive(hook_body)
        hook_body = hook_body[:_next].strip()
        if not hook_body:
            continue
        hook_body, guards = _parse_guards(hook_body)
        entry = {'kind': 'hook', 'name': name, 'timing': timing, 'body': hook_body, 'guards': guards, 'mod_file': mod_file}
        mod_hook_list.append(entry)
        _register_conflict(conflict_map, name, mod_file, f'Hook ({timing})')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Hook [{name}]')

    # ---- Rename Passage [OldName]: NewName ----
    # Updates the name= attribute on the named passage's opening tag.
    # Tier S: anchors on passage name only -- zero porting cost if the old name exists.
    # If the old name is not found, logs a failure (passage may have already been renamed).
    rp_chunks = re.split(r'(?m)^Rename Passage \[', mod_content)
    for chunk in rp_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        old_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        new_name_raw = rest[:first_nl].strip() if first_nl != -1 else rest.strip()
        if not new_name_raw:
            continue
        new_name_raw, guards = _parse_guards(new_name_raw)
        new_name = new_name_raw.strip()
        if not new_name:
            continue
        entry = {
            'kind':     'rename_passage',
            'name':     old_name,
            'new_name': new_name,
            'guards':   guards,
            'mod_file': mod_file,
        }
        mod_func_list.append(entry)
        label = f'Rename Passage [{old_name}]: {new_name}'
        _register_conflict(conflict_map, label, mod_file, 'Rename Passage')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Add Variable [varname]: value ----
    # Injects <<set $varname to value>> into StoryInit if not already present.
    # Tier 1: safe to re-run; skipped if the variable name already appears in StoryInit.
    # Saves mod authors from using Append To Passage [StoryInit]: for simple var declarations.
    av_chunks = re.split(r'(?m)^Add Variable \[', mod_content)
    for chunk in av_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        varname = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        value_raw = rest[:first_nl].strip() if first_nl != -1 else rest.strip()
        if not varname:
            continue
        value_raw, guards = _parse_guards(value_raw)
        value = value_raw.strip()
        entry = {
            'kind':    'add_variable',
            'name':    varname,
            'value':   value,
            'guards':  guards,
            'mod_file': mod_file,
        }
        mod_func_list.append(entry)
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Add Variable [{varname}]')

    # ---- Insert Into Function [funcname]: anchor / With: body ----
    # Scoped Insert After that only matches inside the named function body.
    # Prevents false matches when the anchor string appears in multiple functions.
    # Tier 2.5: resilient to function body changes as long as the anchor survives.
    iif_chunks = re.split(r'(?m)^Insert Into Function \[', mod_content)
    for chunk in iif_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        func_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        with_m = re.search(r'(?m)^With:\s*$', rest)
        if not with_m:
            continue
        anchor_raw = rest[:with_m.start()].strip()
        if not anchor_raw:
            continue
        rest_after = rest[with_m.end():]
        _next = _find_next_directive(rest_after)
        body_raw = rest_after[:_next].strip()
        if not body_raw:
            continue
        body_raw, guards = _parse_guards(body_raw)
        entry = {
            'kind':      'insert_into_func',
            'name':      func_name,
            'anchor':    anchor_raw,
            'body':      body_raw,
            'guards':    guards,
            'mod_file':  mod_file,
        }
        mod_func_list.append(entry)
        label = f'Insert Into Function [{func_name}]: {anchor_raw[:40]}'
        _register_conflict(conflict_map, label, mod_file, 'Insert Into Function')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Replace Function Signature [funcname]: new params ----
    # Replaces only the parameter list of a named function, leaving the body intact.
    # Solves the case where a mod adds new parameters (e.g. setup.random_name gains
    # ethnicity, traitassocid) without needing to own the full function body.
    # Tier 3: anchors on function name -- same resilience as Replace Function.
    rfs_chunks = re.split(r'(?m)^Replace Function Signature \[', mod_content)
    for chunk in rfs_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        func_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        new_params_raw = rest[:first_nl].strip() if first_nl != -1 else rest.strip()
        if not new_params_raw:
            continue
        new_params_raw, guards = _parse_guards(new_params_raw)
        new_params = new_params_raw.strip()
        if not new_params:
            continue
        entry = {
            'kind':       'replace_func_sig',
            'name':       func_name,
            'new_params': new_params,
            'guards':     guards,
            'mod_file':   mod_file,
        }
        mod_func_list.append(entry)
        label = f'Replace Function Signature [{func_name}]'
        _register_conflict(conflict_map, label, mod_file, 'Replace Function Signature')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Clone Passage [SourceName] As [DestName]: (v0.7.1) ----
    # Copies an existing passage body (vanilla or mod-added) and registers it
    # under a new name.  Tier S -- anchors on passage name only.
    cp_chunks = re.split(r'(?m)^Clone Passage \[', mod_content)
    for chunk in cp_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        rest_line = chunk[bracket_end + 2:].split('\n', 1)[0].strip()
        src_name = chunk[:bracket_end].strip()
        as_m = re.match(r'^As\s+\[(.+?)\]', rest_line, re.IGNORECASE)
        if not as_m:
            continue
        dst_name = as_m.group(1).strip()
        rest_after = chunk[bracket_end + 2 + len(rest_line):]
        _next = _find_next_directive(rest_after)
        body_raw = rest_after[:_next].strip()
        body_raw, guards = _parse_guards(body_raw)
        entry = {
            'kind':     'clone_passage',
            'name':     src_name,
            'new_name': dst_name,
            'guards':   guards,
            'mod_file': mod_file,
        }
        mod_func_list.append(entry)
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Clone Passage [{src_name}] As [{dst_name}]')

    # ---- Wrap Passage [PassageName]: (v0.7.1) ----
    # Injects content at the very start (before:) or end (after:) of a named
    # passage without touching its body.  Symmetric to Hook but for passages.
    wp_chunks = re.split(r'(?m)^Wrap Passage \[', mod_content)
    for chunk in wp_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        psg_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        rest = rest[first_nl + 1:] if first_nl != -1 else ''
        _next = _find_next_directive(rest)
        body_raw = rest[:_next].strip()
        body_raw, guards = _parse_guards(body_raw)
        # Parse before: / after: sub-keys from the body
        before_m = re.search(r'(?m)^before:\s*$', body_raw)
        after_m  = re.search(r'(?m)^after:\s*$',  body_raw)
        timing   = 'before' if before_m else ('after' if after_m else 'after')
        # Strip the timing keyword line itself from the body
        body_clean = re.sub(r'(?m)^(before|after):\s*\n?', '', body_raw).strip()
        if not body_clean:
            continue
        entry = {
            'kind':         'wrap_passage',
            'name':         psg_name,
            'timing':       timing,
            'body':         body_clean,
            'guards':       guards,
            'mod_file':     mod_file,
        }
        mod_func_list.append(entry)
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Wrap Passage [{psg_name}] ({timing})')

    # ---- Replace In All Passages [tag]: (v0.7.1) ----
    # Applies Replace In Passage to every passage that carries the named tag.
    # Anchor and With: body follow the same format as Replace In Passage.
    riap_chunks = re.split(r'(?m)^Replace In All Passages \[', mod_content)
    for chunk in riap_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        tag_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        with_m = re.search(r'(?m)^With:\s*$', rest)
        if not with_m:
            continue
        anchor_raw = rest[:with_m.start()].strip()
        if not anchor_raw:
            continue
        rest_after = rest[with_m.end():]
        _next = _find_next_directive(rest_after)
        body_raw = rest_after[:_next].strip()
        if not body_raw:
            continue
        body_raw, guards = _parse_guards(body_raw)
        entry = {
            'kind':     'replace_in_all_passages',
            'name':     tag_name,
            'anchor':   anchor_raw,
            'body':     body_raw,
            'guards':   guards,
            'mod_file': mod_file,
        }
        mod_func_list.append(entry)
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Replace In All Passages [{tag_name}]: {anchor_raw[:40]}')

    # ---- Add StoryVar [varName]: (v0.7.1) ----
    # Marks a SugarCube story variable as save-persistent by adding it to
    # setup.saveStateFields (or the equivalent SugarCube Save API). Also
    # injects a <<set $var to value>> into StoryInit, like Add Variable,
    # so the var is both initialized AND save-tracked in one directive.
    # Format: Add StoryVar [varName]: defaultValue
    asv_chunks = re.split(r'(?m)^Add StoryVar \[', mod_content)
    for chunk in asv_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        varname = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        value_raw = rest[:first_nl].strip() if first_nl != -1 else rest.strip()
        value_raw, guards = _parse_guards(value_raw)
        value = value_raw.strip()
        if not varname:
            continue
        entry = {
            'kind':     'add_storyvar',
            'name':     varname,
            'value':    value,
            'guards':   guards,
            'mod_file': mod_file,
        }
        mod_func_list.append(entry)
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Add StoryVar [{varname}]')

    # ---- Add Function [name]: blocks ----
    # Injects a new named function into the script block.
    # Unlike Replace Function, this never overwrites existing code --
    # if a function with this name already exists it is skipped.
    af_chunks = re.split(r'(?m)^Add Function \[', mod_content)
    for chunk in af_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        first_nl = rest.find('\n')
        rest = rest[first_nl + 1:] if first_nl != -1 else ''
        _next = _find_next_directive(rest)
        body = rest[:_next].strip()
        if not body:
            continue
        body, guards = _parse_guards(body)
        entry = {'kind': 'add_func', 'name': name, 'body': body, 'guards': guards, 'mod_file': mod_file}
        mod_func_list.append(entry)
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(f'Add Function [{name}]')

    # ---- Replace In Function [funcname]: anchor / With: body ----
    # Scoped replacement that only matches inside the named function body.
    # Like Insert Into Function but replaces the anchor instead of inserting after it.
    # Tier 2.5: anchors on function name + anchor string.
    rif_chunks = re.split(r'(?m)^Replace In Function \[', mod_content)
    for chunk in rif_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        func_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        with_m = re.search(r'(?m)^With:\s*$', rest)
        if not with_m:
            continue
        anchor_raw = rest[:with_m.start()].strip()
        if not anchor_raw:
            continue
        rest_after = rest[with_m.end():]
        _next = _find_next_directive(rest_after)
        body_raw = rest_after[:_next].strip()
        if not body_raw:
            continue
        body_raw, guards = _parse_guards(body_raw)
        entry = {
            'kind':      'replace_in_func',
            'name':      func_name,
            'anchor':    anchor_raw,
            'body':      body_raw,
            'guards':    guards,
            'mod_file':  mod_file,
        }
        mod_func_list.append(entry)
        label = f'Replace In Function [{func_name}]: {anchor_raw[:40]}'
        _register_conflict(conflict_map, label, mod_file, 'Replace In Function')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Delete In Passage [PassageName]: anchor ----
    # Scoped deletion that removes the anchor text from the named passage body.
    # No With: body needed -- pure deletion.
    # Tier 2.5: anchors on passage name + anchor string.
    dip_chunks = re.split(r'(?m)^Delete In Passage \[', mod_content)
    for chunk in dip_chunks[1:]:
        bracket_end = chunk.find(']:')
        if bracket_end == -1:
            continue
        passage_name = chunk[:bracket_end].strip()
        rest = chunk[bracket_end + 2:]
        # Anchor is everything up to the next directive or end of content
        _next = _find_next_directive(rest)
        # Strip leading newline from rest
        first_nl = rest.find('\n')
        anchor_start = first_nl + 1 if first_nl != -1 else 0
        anchor_raw = rest[anchor_start:_next].strip()
        if not anchor_raw:
            continue
        anchor_raw, guards = _parse_guards(anchor_raw)
        # Encode anchor the same way as Replace In Passage targets
        anchor_e = escape_twine_tags(escape_html_between_tags(anchor_raw))
        anchor_e = auto_escape_passage_bodies(anchor_e.strip())
        entry = {
            'kind':         'delete_in_passage',
            'passage_name': passage_name,
            'name':         anchor_e,
            'guards':       guards,
            'mod_file':     mod_file,
        }
        mod_func_list.append(entry)
        label = f'Delete In Passage [{passage_name}]: {anchor_e[:40]}'
        _register_conflict(conflict_map, label, mod_file, 'Delete In Passage')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

    # ---- Move Passage [OldName] To [NewName]: ----
    # Renames the passage AND updates all <<goto>>, <<link>>, and passage:
    # references throughout the HTML.  Tier S: zero porting cost.
    mp_chunks = re.split(r'(?m)^Move Passage \[', mod_content)
    for chunk in mp_chunks[1:]:
        first_bracket = chunk.find(']')
        if first_bracket == -1:
            continue
        old_name = chunk[:first_bracket].strip()
        rest = chunk[first_bracket + 1:].lstrip()
        if not rest.startswith('To ['):
            continue
        rest = rest[len('To ['):]
        end_bracket = rest.find(']:')
        if end_bracket == -1:
            continue
        new_name = rest[:end_bracket].strip()
        if not old_name or not new_name:
            continue
        rest_after = rest[end_bracket + 2:]
        first_nl = rest_after.find('\n')
        guard_text = rest_after[:first_nl] if first_nl != -1 else rest_after
        _, guards = _parse_guards(guard_text)
        entry = {
            'kind':     'move_passage',
            'name':     old_name,
            'new_name': new_name,
            'guards':   guards,
            'mod_file': mod_file,
        }
        mod_func_list.append(entry)
        label = f'Move Passage [{old_name}] To [{new_name}]'
        _register_conflict(conflict_map, label, mod_file, 'Move Passage')
        if mod_file not in mod_file_indexes:
            mod_file_indexes[mod_file] = []
        mod_file_indexes[mod_file].append(label)

def _parse_mod_header(mod_content: str) -> dict:
    """
    Change 2: Parse structured [Mod] / # Key: Value header from a mod file.

    Recognises both formats in the header region (lines before the first
    non-comment content):

      # Key: Value          -- comment-prefixed key/value (original style)
      [Mod]                 -- optional section marker, ignored
      Key: Value            -- bare key/value (DoggyPatcher-inspired style)

    Recognised keys (case-insensitive):
      Name, Version, Author, Target -- informational
      Modifies   -- CSV of passage/function names this mod touches
      Priority   -- integer; lower numbers load earlier within same
                    topological tier (default 1000). CM recommended field.
      Requires   -- CSV of hard dependency mod filenames. For CM mods,
                    use cm_dependencies.json or a sidecar .json instead --
                    those feed the full topological sort. Requires: here
                    only emits a load-time warning; it does not affect order.

    Returns a dict with normalised lowercase keys.  Missing keys are absent.
    Complexity: O(H) single pass where H = header line count (<< 1% of file).
    """
    result = {}
    _csv_keys = {'modifies', 'requires'}
    _in_mod_section = False   # True after [Mod] marker seen
    for line in mod_content.splitlines():
        stripped = line.strip()
        if stripped == '[Mod]':
            _in_mod_section = True
            continue
        # End of header: first non-comment, non-blank line outside [Mod] section
        if not stripped.startswith('#'):
            if not stripped:
                continue  # blank lines are fine in header
            if not _in_mod_section:
                break  # non-comment content before [Mod] = end of header
            # Inside [Mod] section: check for end of section
            if stripped.startswith('['):
                break  # new section = end of [Mod] block
            # Allow bare "Key: Value" inside [Mod] section
            content = stripped
        else:
            # Strip leading # and optional whitespace
            content = re.sub(r'^#+\s*', '', stripped)
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_ -]*)\s*:\s*(.+)$', content)
        if not m:
            continue
        key = m.group(1).strip().lower().replace(' ', '_').replace('-', '_')
        val = m.group(2).strip()
        if key in _csv_keys:
            result[key] = [p.strip() for p in val.split(',') if p.strip()]
        elif key == 'priority':
            try:
                result['priority'] = int(val)
            except ValueError:
                pass  # malformed priority -- silently ignore
        else:
            # Normalise 'mod_name' -> 'name' so both '# Name:' and
            # '# Mod Name:' produce result['name']
            if key == 'mod_name':
                key = 'name'
            result[key] = val
    return result


def _parse_modifies_header(mod_content: str) -> list:
    """Backward-compat wrapper -- returns Modifies: list from mod header."""
    return _parse_mod_header(mod_content).get('modifies', [])


#Function to Load and Process All Mod Files
def load_mods(mods_folder):
    # Variables
    mod_dict = {}
    mod_list = []          # v0.7.6: ordered list of (old_key, source_mod) -- preserves duplicates
    mod_file_indexes = {}  # Track the mod file and the index of its replacements in mod_dict
    mod_reg_list = []      # List of ReplaceReg entries (regex group replacements)
    mod_struct_list = []   # List of Append Array / Append Variable/Function to Class entries
    mod_func_list = []     # List of Replace Function / Insert Before / Insert After / Delete Block entries
    mod_hook_list = []     # List of Hook [] entries (function wrapping)
    conflict_map = {}      # Maps target name -> list of (mod_file, kind) for conflict detection
    _modifies_map: dict = {}  # Plan 1.11: declared Modifies: targets -> [mod_file]

    # v0.6.0: First-class registries for accumulator directives
    passage_registry = []   # ordered list preserving mod load order
    passage_names_seen = {} # name -> index into passage_registry for O(1) duplicate detection
    js_registry = []        # ordered list of Add Javascript blocks
    css_registry = []       # ordered list of Add CSS blocks
    events_registry = []    # ordered list of Add Events blocks
    key_to_mod = {}         # Part C: mod_dict key -> source mod file for O(1) cleanup

    # v0.7.0: deterministic load order via resolve_mod_load_order.
    # Respects [load_order] from kitty_config.toml; falls back to alphabetical.
    # Accepts .mod, .kdiff, and .patch extensions.
    ordered_mod_paths = resolve_mod_load_order(mods_folder, _kitty_cfg)

    # Load global .json registry once for Requires: coverage check below.
    # cm_dependencies.json covers CM mods -- third-party mods without .json
    # coverage can use Requires: in their header to get a load-time warning.
    _global_dep_registry = _load_global_registry(mods_folder)
    _loaded_basenames = {os.path.basename(p) for p in ordered_mod_paths}

    successful_mod_files = []  # Track the successful mod files

    # v0.7.1: parallel mod parsing.
    # Phase 1: Parse each mod file into a local scratch namespace concurrently.
    #   - load_mod_source (file I/O + decryption) runs in parallel.
    #   - proc_replacement_old/new build per-mod local copies of all registries.
    # Phase 2: Merge local results into shared registries in load order.
    #   - Load order is preserved because we iterate ordered_mod_paths.
    #   - All shared state (mod_dict, passage_registry, conflict_map, etc.)
    #     is only written during the sequential merge phase.

    def _parse_one_mod(mod_path):
        """Parse one mod file into a local scratch namespace. Pure function -- no shared writes."""
        mod_file    = os.path.basename(mod_path)
        mod_content = load_mod_source(mod_path, dist_secret=_KITTY_DIST_SECRET)

        # Local scratch registries
        _local_mod_dict          = {}
        _local_mod_list          = []   # v0.7.6: ordered insertion list
        _local_mod_file_indexes  = {}
        _local_mod_reg_list      = []
        _local_mod_struct_list   = []
        _local_mod_func_list     = []
        _local_mod_hook_list     = []
        _local_conflict_map      = {}
        _local_passage_registry  = []
        _local_passage_names_seen = {}
        _local_js_registry       = []
        _local_css_registry      = []
        _local_events_registry   = []
        _local_key_to_mod        = {}

        proc_replacement_old(
            mod_content, _local_mod_dict, _local_mod_list, _local_mod_file_indexes, mod_file,
            conflict_map=_local_conflict_map, key_to_mod=_local_key_to_mod
        )
        proc_replacement_new(
            mod_content, _local_mod_dict, _local_mod_list, _local_mod_file_indexes, mod_file,
            _local_mod_reg_list, _local_mod_struct_list, _local_mod_func_list,
            _local_mod_hook_list, _local_conflict_map, _local_passage_registry,
            _local_passage_names_seen, _local_js_registry, _local_css_registry,
            _local_events_registry, _local_key_to_mod
        )

        _mod_hdr = _parse_mod_header(mod_content)

        return {
            'mod_path':            mod_path,
            'mod_file':            mod_file,
            'mod_content':         mod_content,
            'mod_hdr':             _mod_hdr,
            'mod_dict':            _local_mod_dict,
            'mod_list':            _local_mod_list,
            'mod_file_indexes':    _local_mod_file_indexes,
            'mod_reg_list':        _local_mod_reg_list,
            'mod_struct_list':     _local_mod_struct_list,
            'mod_func_list':       _local_mod_func_list,
            'mod_hook_list':       _local_mod_hook_list,
            'conflict_map':        _local_conflict_map,
            'passage_registry':    _local_passage_registry,
            'passage_names_seen':  _local_passage_names_seen,
            'js_registry':         _local_js_registry,
            'css_registry':        _local_css_registry,
            'events_registry':     _local_events_registry,
            'key_to_mod':          _local_key_to_mod,
        }

    # Determine parallelism: use min(mod count, 8) threads.
    # I/O-bound phase benefits from threads even under GIL.
    _n_workers = max(1, min(len(ordered_mod_paths), 8))

    # Submit all parse jobs and collect futures keyed by mod_path for ordering.
    _futures = {}
    with ThreadPoolExecutor(max_workers=_n_workers) as _pool:
        for _mp in ordered_mod_paths:
            _futures[_mp] = _pool.submit(_parse_one_mod, _mp)

    # Sequential merge in load order (preserves determinism).
    for mod_path in ordered_mod_paths:
        parsed = _futures[mod_path].result()  # blocks until that mod's parse is done

        mod_file   = parsed['mod_file']
        _mod_hdr   = parsed['mod_hdr']

        # Modifies: tracking
        for _declared in _mod_hdr.get('modifies', []):
            _modifies_map.setdefault(_declared, []).append(mod_file)

        # Requires: validation
        _mod_stem = _stem(mod_file)
        _has_json_coverage = (
            _mod_stem in _global_dep_registry or
            os.path.exists(os.path.splitext(mod_path)[0] + '.json')
        )
        if not _has_json_coverage:
            for _req in _mod_hdr.get('requires', []):
                _optional = _req.startswith('?')
                _req_clean = _req.lstrip('?').strip()
                _found = any(
                    os.path.splitext(b)[0].lower() ==
                    os.path.splitext(_req_clean)[0].lower()
                    or b.lower() == _req_clean.lower()
                    for b in _loaded_basenames
                )
                if not _found and not _optional:
                    handle_output(
                        f"DEPENDENCY WARNING: {mod_file} declares "
                        f"Requires: '{_req_clean}' which is not in the "
                        f"mods folder. Add a sidecar {mod_file[:-4] if '.mod' in mod_file else mod_file}.json "
                        f"or entry in cm_dependencies.json for load-order "
                        f"enforcement. Anchor failures may follow.",
                        "alllogs"
                    )

        # Merge parsed results into shared registries (sequential, in load order)
        mod_dict.update(parsed['mod_dict'])
        # v0.7.6: extend mod_list preserving all entries including duplicates;
        # emit ORDERING WARNING for any OLD anchor already seen from a prior mod.
        _existing_keys = {k for k, _ in mod_list}
        for _mk, _msrc in parsed['mod_list']:
            if _mk in _existing_keys:
                _prior_mods = ', '.join(_msrc2 for _mk2, _msrc2 in mod_list if _mk2 == _mk)
                handle_output(
                    f"ORDERING WARNING: Multiple mods inject at anchor "
                    f"'{_mk[:80].strip()}' -- load-order determines injection sequence: "
                    f"{_prior_mods}, {_msrc}. "
                    f"Consider [ONCE] modifier if only one injection is intended.",
                    "alllogs"
                )
            _existing_keys.add(_mk)
        mod_list.extend(parsed['mod_list'])
        for k, v in parsed['mod_file_indexes'].items():
            mod_file_indexes.setdefault(k, []).extend(v)
        mod_reg_list.extend(parsed['mod_reg_list'])
        mod_struct_list.extend(parsed['mod_struct_list'])
        mod_func_list.extend(parsed['mod_func_list'])
        mod_hook_list.extend(parsed['mod_hook_list'])
        for k, v in parsed['conflict_map'].items():
            conflict_map.setdefault(k, []).extend(v)
        # Passage registry: deduplicate by name
        for prec in parsed['passage_registry']:
            pname = prec.get('name', '')
            if pname and pname not in passage_names_seen:
                passage_names_seen[pname] = len(passage_registry)
                passage_registry.append(prec)
        js_registry.extend(parsed['js_registry'])
        css_registry.extend(parsed['css_registry'])
        events_registry.extend(parsed['events_registry'])
        key_to_mod.update(parsed['key_to_mod'])

        successful_mod_files.append(mod_file)

    # ---- Cross-mod inner replacement pass (v0.6.0 optimized) ----
    # After ALL mods are loaded, run a final multi-pass inner replacement sweep across
    # the entire mod_dict.  This allows a Replace: block in mod B to target content
    # that only exists inside mod A's With: body -- the per-mod pass inside
    # proc_replacement_new cannot see other mods' bodies since they weren't loaded yet.
    #
    # v0.6.0: Build inner_candidates index from all mod_dict entries, then iterate
    # only over candidate pairs instead of the full Cartesian product.
    _raw_targets = {"</script><tw-passagedata", "</style><script", "setup.Events.db =\n["}
    all_cross_inner_keys = []
    MAX_CROSS_PASSES = 20

    # Build cross-mod inner_candidates index
    cross_candidates = {}
    all_keys_list = list(mod_dict.keys())

    for search_key in all_keys_list:
        escaped_key = escape_twine_tags(search_key)
        candidates = set()
        for host_key in all_keys_list:
            if host_key == search_key:
                continue
            host_body = mod_dict[host_key][0]
            host_is_raw = host_key in _raw_targets
            actual_search = search_key if host_is_raw else escaped_key
            if actual_search in host_body:
                candidates.add(host_key)
        if candidates:
            cross_candidates[search_key] = candidates

    for _pass in range(MAX_CROSS_PASSES):
        cross_inner_keys = []

        for search_key in list(cross_candidates.keys()):
            if search_key not in mod_dict or search_key in all_cross_inner_keys:
                continue
            search_entry = mod_dict[search_key]
            search_new = search_entry[0]
            escaped_key = escape_twine_tags(search_key)
            host_keys = cross_candidates.get(search_key, set())

            for host_key in list(host_keys):
                if host_key == search_key or host_key not in mod_dict:
                    continue
                host_entry = mod_dict[host_key]
                host_body = host_entry[0]
                host_is_raw = host_key in _raw_targets

                actual_search = search_key if host_is_raw else escaped_key
                inject_new = search_new.replace('&lt;&lt;', '<<').replace('&gt;&gt;', '>>').replace('&gt;', '>').replace('&lt;', '<').replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'") if host_is_raw else search_new

                if actual_search in host_body:
                    new_body = host_body.replace(actual_search, inject_new, 1)
                    mod_dict[host_key] = (new_body, host_entry[1])
                    cross_inner_keys.append(search_key)
                    # Part C: O(1) cleanup via key_to_mod
                    source_mod = key_to_mod.get(search_key)
                    if source_mod and source_mod in mod_file_indexes and search_key in mod_file_indexes[source_mod]:
                        mod_file_indexes[source_mod].remove(search_key)
                    # Update cross_candidates for newly created matches
                    for other_key in list(cross_candidates.keys()):
                        if other_key != search_key and other_key not in all_cross_inner_keys:
                            ek = escape_twine_tags(other_key)
                            ak = other_key if host_is_raw else ek
                            if ak in new_body:
                                cross_candidates.setdefault(other_key, set()).add(host_key)
                    break

        if not cross_inner_keys:
            break  # fixed point reached

        all_cross_inner_keys.extend(cross_inner_keys)
        for k in cross_inner_keys:
            mod_dict.pop(k, None)
            cross_candidates.pop(k, None)

    # ---- v0.7.0 Plan 1.11: Modifies: pre-flight conflict warnings ----
    for _tgt, _mods in sorted(_modifies_map.items()):
        if len(_mods) > 1:
            _mods_str = ', '.join(os.path.basename(m) for m in _mods)
            handle_output(
                f'PRE-FLIGHT CONFLICT: Multiple mods declare Modifies: {_tgt} '
                f'-- {_mods_str}',
                'log'
            )

    # ---- v0.7.0 Plan 1.9: cross-mod passage ownership map ----
    # Maps passage/function name -> list of (mod_file, kind) for conflict display.
    # Logged at verbose level; exposed to Toolbench for pre-flight conflict panel.
    if _verbose_logging:
        _ownership: dict = {}
        for entry in mod_func_list:
            _tgt = entry.get('passage_name') or entry.get('name', '')
            if _tgt:
                _ownership.setdefault(_tgt, []).append(
                    (entry.get('mod_file', '?'), entry.get('kind', '?'))
                )
        for _tgt, _owners in sorted(_ownership.items()):
            if len(_owners) > 1:
                _mods_str = ', '.join(f'{mf} ({k})' for mf, k in _owners)
                handle_output(f'[ownership] {_tgt} <- {_mods_str}', 'log')

    return mod_dict, mod_list, mod_file_indexes, successful_mod_files, mod_reg_list, mod_struct_list, mod_func_list, mod_hook_list, conflict_map, passage_registry, passage_names_seen, js_registry, css_registry, events_registry, key_to_mod


# ------------------------------------------------
# Pid generator / normalizer
# ------------------------------------------------

def _get_max_pid(html_content):
    """Return the highest integer pid currently in html_content."""
    pids = []
    for m in re.finditer(r'<tw-passagedata[^>]+pid="([^"]+)"', html_content):
        try:
            pids.append(int(m.group(1)))
        except ValueError:
            pass  # string pids like "BnF-1" are skipped
    return max(pids) if pids else 0


def _resolve_auto_pids(text, next_pid):
    """
    Replace every occurrence of pid="auto" in text with sequential integer pids
    starting at next_pid.  Returns (modified_text, new_next_pid).
    """
    result = []
    pos = 0
    for m in re.finditer(r'pid="auto"', text, re.IGNORECASE):
        result.append(text[pos:m.start()])
        result.append(f'pid="{next_pid}"')
        next_pid += 1
        pos = m.end()
    result.append(text[pos:])
    return ''.join(result), next_pid


def _renormalize_pids(html_content):
    """
    Renumber every <tw-passagedata pid="..."> sequentially (1, 2, 3...)
    in document order and return the modified html_content.

    Also updates the startnode attribute in <tw-storydata> to match the
    new PID of whichever passage was originally the startnode.

    Safe because SugarCube identifies passages by name, not pid.
    Renormalizing keeps the HTML valid for the Twine editor and eliminates
    cosmetic tag-imbalance warnings caused by some mod injection patterns.

    Edge case (v0.5.3): passages missing pid= entirely (e.g. a mod With: body
    that omitted the attribute) are assigned a placeholder pid="0" before
    renumbering so they are included in the sequential pass rather than left
    unnumbered in the output.
    """
    # Fix passages missing pid= entirely -- inject pid="0" as placeholder
    # so the renumbering pass below includes them in document order.
    # Pattern matches <tw-passagedata ...> tags that have no pid= attribute.
    _pidless = _get_compiled(r'(<tw-passagedata\b(?![^>]*\bpid=)[^>]*>)', re.DOTALL)
    def _inject_pid(m):
        tag = m.group(1)
        # Insert pid="0" after the opening tag name
        return re.sub(r'(<tw-passagedata)', r'\1 pid="0"', tag, count=1)

    pidless_count = len(_pidless.findall(html_content))
    if pidless_count:
        html_content = _pidless.sub(_inject_pid, html_content)
        handle_output(
            f"PID WARNING: {pidless_count} passage(s) had no pid= attribute -- "
            f"assigned placeholder pid=\"0\" before renormalization.", "alllogs"
        )

    # Extract the original startnode value
    sn_match = re.search(r'<tw-storydata[^>]+startnode="([^"]+)"', html_content)
    old_startnode = sn_match.group(1) if sn_match else None

    # Build old -> new PID mapping while renumbering
    counter = [0]
    pid_map = {}

    def _pid_replacer(m):
        old_pid = m.group(2)
        counter[0] += 1
        new_pid = str(counter[0])
        pid_map[old_pid] = new_pid
        return m.group(1) + new_pid + m.group(3)

    pattern = _get_compiled(r'(<tw-passagedata[^>]+pid=")([^"]+)(")')
    result = pattern.sub(_pid_replacer, html_content)

    # Update startnode to the new PID
    if old_startnode and old_startnode in pid_map:
        new_startnode = pid_map[old_startnode]
        result = re.sub(
            r'(<tw-storydata[^>]+startnode=")([^"]+)(")',
            lambda m: m.group(1) + new_startnode + m.group(3),
            result,
            count=1
        )

    return result


def _detect_pid_collisions(mod_dict, html_content, passage_registry=None, passage_meta=None):
    """
    Warn when a mod injects a new passage with a pid that already exists in
    the game HTML, or when two mod entries claim the same hardcoded pid.
    v0.6.0: Scans passage_registry instead of </tw-storydata> accumulator.
    """
    # v0.7.2: extract pids from _passage_meta open tags (already parsed) instead
    # of re.finditer over 20MB html_content.
    existing_pids = set()
    if passage_meta:
        for _pname, (_open_tag, _, _) in passage_meta.items():
            _pm = re.search(r'pid="([^"]+)', _open_tag)
            if _pm:
                existing_pids.add(_pm.group(1))
    else:
        for m in re.finditer(r'<tw-passagedata[^>]+pid="([^"]+)"', html_content):
            existing_pids.add(m.group(1))

    # Scan passage_registry for hardcoded pids (non-auto)
    if passage_registry:
        seen = {}
        for rec in passage_registry:
            pid = rec.get('pid', 'auto')
            if pid.lower() == 'auto':
                continue
            source = rec.get('mod_file', 'unknown')
            if pid in existing_pids:
                handle_output(
                    f'PID WARNING: new passage \'{rec["name"]}\' from {source} uses pid="{pid}" '
                    f'which already exists in the game HTML.',
                    'alllogs'
                )
            elif pid in seen:
                handle_output(
                    f'PID WARNING: pid="{pid}" claimed by both {seen[pid]} and {source}.',
                    'alllogs'
                )
            else:
                seen[pid] = source

def _resolve_auto_passage_attrs(apply_lines, html_content, pname):
    """
    Resolve pid="auto" and position="auto" in the With: body of a passage
    replacement by looking up the live values from html_content for the
    named passage.

    Called just before apply_lines is written into html_content so the
    patched HTML never contains literal 'auto' attribute values.

    If the passage is not found in html_content (new passage being added
    via Replace: rather than Add Passage:), pid falls back to the next
    available integer and position falls back to "0,0".
    """
    if 'pid="auto"' not in apply_lines and 'position="auto"' not in apply_lines:
        return apply_lines

    live_tag_m = re.search(
        r'<tw-passagedata[^>]*name="' + re.escape(pname) + r'"[^>]*>',
        html_content
    )

    if live_tag_m:
        live_tag = live_tag_m.group(0)
        live_pid_m = re.search(r'pid="([^"]+)"',      live_tag)
        live_pos_m = re.search(r'position="([^"]+)"', live_tag)
        live_pid   = live_pid_m.group(1) if live_pid_m else None
        live_pos   = live_pos_m.group(1) if live_pos_m else '0,0'
    else:
        # Passage not in HTML yet -- assign a fresh pid and default position
        live_pid = str(_get_max_pid(html_content) + 1)
        live_pos = '0,0'

    if 'pid="auto"' in apply_lines and live_pid:
        apply_lines = re.sub(r'pid="auto"', f'pid="{live_pid}"', apply_lines, count=1)
        handle_output(
            f"Auto-resolved pid=\"auto\" -> pid=\"{live_pid}\" for passage '{pname}'", "log"
        )

    if 'position="auto"' in apply_lines:
        apply_lines = re.sub(r'position="auto"', f'position="{live_pos}"', apply_lines, count=1)
        handle_output(
            f"Auto-resolved position=\"auto\" -> position=\"{live_pos}\" for passage '{pname}'", "log"
        )

    return apply_lines


def _log_opening_tag_diff(mod_tag, game_tag, pname, pid):
    """
    Compare the tw-passagedata opening tag from the mod's Replace: target
    against the tag currently in the game HTML.  Logs each attribute that
    differs (pid, name, tags, position, size) with before/after values.
    Called only when pid+name both confirm it is the same passage.
    """
    attrs = ('pid', 'name', 'tags', 'position', 'size')
    lines = [f"PID MATCH: passage '{pname}' (pid={pid}) found in game HTML."]
    lines.append("  Opening tag attribute comparison:")
    any_diff = False
    for attr in attrs:
        mod_m  = re.search(rf'{attr}="([^"]*)"', mod_tag)
        game_m = re.search(rf'{attr}="([^"]*)"', game_tag)
        mod_v  = mod_m.group(1)  if mod_m  else '(absent)'
        game_v = game_m.group(1) if game_m else '(absent)'
        if mod_v != game_v:
            lines.append(f"    {attr:<10}: {mod_v!r}  ->  {game_v!r}")
            any_diff = True
        else:
            lines.append(f"    {attr:<10}: {mod_v!r}  (unchanged)")
    if not any_diff:
        lines.append("    (all attributes identical -- mismatch is in passage body content)")
    handle_output("\n".join(lines), "log")


#Function to Replace the Content in the HTML File

def find_passage_imbalance(html_content):
    """
    Walk through the HTML and stop at the exact point where
    </tw-passagedata> exceeds <tw-passagedata>.
    Only called when an imbalance is detected. Prints the offending
    line and surrounding context to stdout for diagnosis.
    """
    open_count = 0
    close_count = 0
    lines = html_content.split('\n')
    for i, line in enumerate(lines, 1):
        opens = line.count('<tw-passagedata')
        closes = line.count('</tw-passagedata>')
        open_count += opens
        close_count += closes
        if close_count > open_count:
            print("\n=== PASSAGE TAG IMBALANCE ===")
            print(f"Line {i}: {open_count} open vs {close_count} close")
            print("\nProblem line:")
            print(line.strip())
            print("\nContext:")
            start = max(0, i - 3)
            end = min(len(lines), i + 2)
            for j in range(start, end):
                print(f"  {j+1}: {lines[j]}")
            return i
    print("\nNo early imbalance found.")
    return None



def _check_mod_duplicates(mod_dict, mod_func_list, mod_file_indexes=None, js_registry=None, events_registry=None):
    """Scan parsed mod content for common duplicate errors.
    v0.6.0: Macro.add scans js_registry; event passage scans events_registry;
    passage duplicate detection is handled by passage_names_seen at extraction
    time and is no longer checked here."""
    warnings = []

    # Macro.add duplicates across all JS injection bodies (v0.6.0: scan js_registry)
    macro_registry = {}
    js_bodies = []
    if js_registry:
        js_bodies = [(e['body'], e['mod_file']) for e in js_registry]
    # Also scan any remaining mod_dict entries (legacy accumulator path)
    for key, entry in mod_dict.items():
        body = entry[0]
        js_bodies.append((body, key[:50]))
    for body, source in js_bodies:
        for macro_name in re.findall(r"""Macro\.add\([\"'](\w+)[\"']""", body):
            macro_registry.setdefault(macro_name, []).append(source)
    for macro_name, sources in macro_registry.items():
        if len(sources) > 1:
            warnings.append((
                f"DUPLICATE MACRO '{macro_name}': registered {len(sources)}x in JS blocks. "
                f"SugarCube ignores registrations after the first -- later definitions are dead code.",
                True
            ))

    # Event passage registration duplicates (v0.6.0: scan events_registry)
    event_passage_counts = {}
    if events_registry:
        for e in events_registry:
            body = e.get('body', '')
            for ep in re.findall(r"""passage:\s*[\"'](\w+)[\"']""", body):
                event_passage_counts[ep] = event_passage_counts.get(ep, 0) + 1
    # Also scan mod_func_list for legacy entries
    for entry in mod_func_list:
        body = entry.get('body', '')
        if 'passage:' not in body:
            continue
        for ep in re.findall(r"""passage:\s*[\"'](\w+)[\"']""", body):
            event_passage_counts[ep] = event_passage_counts.get(ep, 0) + 1
    for ep, cnt in event_passage_counts.items():
        if cnt > 1:
            warnings.append((
                f"DUPLICATE EVENT REGISTRATION '{ep}': registered {cnt}x. "
                f"Will fire at ~{cnt}x intended frequency in-game.",
                True
            ))

    # v0.6.0: All passage duplicate detection is now handled by passage_names_seen
    # at extraction time (Part A.3) and _split_multi_passage_with_body routes to
    # passage_registry.  No accumulator scan needed.

    return warnings


def _resolve_pid_auto_in_anchor(anchor, html_content):
    """
    If anchor contains pid="auto" (or the HTML-encoded form pid=&quot;auto&quot;
    produced by EscapeTwineTags on legacy ~~ entries), look up the actual pid
    from the named passage in html_content and substitute it.

    Also resolves position="auto" / position=&quot;auto&quot; in the anchor the
    same way -- looks up the live position value from the named passage.

    Both raw and encoded forms are handled so ~~ delimiter blocks and new-style
    Replace: directives work identically.

    Returns the resolved anchor, or the original if no passage name is found
    or no match exists.
    """
    # Normalise encoded forms so the rest of the function works uniformly.
    # &quot;auto&quot; -> "auto" for both pid and position checks.
    _has_pid      = 'pid="auto"'      in anchor.lower() or 'pid=&quot;auto&quot;'      in anchor.lower()
    _has_position = 'position="auto"' in anchor.lower() or 'position=&quot;auto&quot;' in anchor.lower()
    if not _has_pid and not _has_position:
        return anchor

    # Extract passage name -- works on both raw and encoded attribute values.
    name_m = re.search(r'name="([^"]+)"', anchor) or re.search(r'name=&quot;([^&]+)&quot;', anchor)
    if not name_m:
        return anchor
    pname = name_m.group(1)
    live_tag_m = re.search(
        r'<tw-passagedata[^>]*name="' + re.escape(pname) + r'"[^>]*>',
        html_content
    )
    if not live_tag_m:
        return anchor
    live_tag = live_tag_m.group(0)

    if _has_pid:
        live_pid_m = re.search(r'pid="([^"]+)"', live_tag)
        if live_pid_m:
            anchor = re.sub(r'pid=&quot;auto&quot;', f'pid="{live_pid_m.group(1)}"', anchor, count=1, flags=re.IGNORECASE)
            anchor = re.sub(r'pid="auto"',           f'pid="{live_pid_m.group(1)}"', anchor, count=1, flags=re.IGNORECASE)

    if _has_position:
        live_pos_m = re.search(r'position="([^"]+)"', live_tag)
        live_pos   = live_pos_m.group(1) if live_pos_m else '0,0'
        anchor = re.sub(r'position=&quot;auto&quot;', f'position="{live_pos}"', anchor, count=1, flags=re.IGNORECASE)
        anchor = re.sub(r'position="auto"',           f'position="{live_pos}"', anchor, count=1, flags=re.IGNORECASE)

    return anchor



def _split_html(html_content):
    """
    Split html_content into three parts for O(1) per-passage access:

      passage_dict : dict[name -> body_str]   -- decoded passage bodies
      passage_meta : dict[name -> (tag_str, attrs_str)]
                       tag_str  = full opening tag e.g. <tw-passagedata pid="1" ...>
                       attrs_str used for reassembly
      script_block : str  -- content of the <script> block (raw JS)
      header       : str  -- everything before the first <tw-passagedata>

    The passage_dict values are the ENCODED bodies as they appear in the HTML
    (i.e. &lt;&lt;macro&gt;&gt; form).  All directive handlers that previously
    called re.search(passage_pat, html_content) now do passage_dict[name]
    instead -- O(1) vs O(n).

    The original html_content string is preserved as the source of truth for
    non-passage directives (Insert After, Hook, Add Function, etc.) that need
    to search across the full string.  After all passage-scoped directives
    complete, _reassemble_html() writes the modified dict bodies back into
    html_content so all subsequent phases see the updated string.
    """
    passage_dict = {}
    passage_meta = {}

    for m in re.finditer(
        r'(<tw-passagedata([^>]*)>)(.*?)(</tw-passagedata>)',
        html_content, re.DOTALL
    ):
        full_open = m.group(1)    # e.g. <tw-passagedata pid="1" name="Foo" ...>
        attrs     = m.group(2)    # everything inside the opening tag
        body      = m.group(3)
        nm = re.search(r'name="([^"]+)"', attrs)
        if nm:
            name = nm.group(1)
            passage_dict[name] = body
            passage_meta[name] = (full_open, m.start(), m.end())

    # Extract script block(s)
    # v0.7.2: findall captures ALL <script> blocks (vanilla main + any twine-user-script
    # or other secondary blocks) and concatenates them.  IfFunctionExists guards search
    # this combined string so functions defined in any script block are visible.
    # Add Function dup detection still works -- injections land in the first block,
    # which is always the start of the concatenation.
    _script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL)
    script_block = '\n'.join(_script_blocks) if _script_blocks else ''

    # Compute max pid during the same passage scan -- avoids a second
    # re.findall pass over the full HTML just for _get_max_pid.
    max_pid = 0
    for name, (full_open, abs_start, abs_end) in passage_meta.items():
        pid_m = re.search(r'pid="([^"]+)"', full_open)
        if pid_m:
            try:
                max_pid = max(max_pid, int(pid_m.group(1)))
            except ValueError:
                pass

    return passage_dict, passage_meta, script_block, max_pid


def _reassemble_html(html_content, passage_dict, passage_meta):
    """
    Write modified passage_dict bodies back into html_content.
    Only passages whose body actually changed are rewritten.
    Uses right-to-left splice on absolute positions so earlier offsets
    stay valid after each substitution.

    Returns the updated html_content string.
    """
    # Collect (start_of_body, end_of_body, new_body) for changed passages
    ops = []
    for name, new_body in passage_dict.items():
        if name not in passage_meta:
            continue
        full_open, abs_start, abs_end = passage_meta[name]
        # Body starts after the opening tag, ends before </tw-passagedata>
        tag_end = abs_start + len(full_open)
        close_tag = '</tw-passagedata>'
        body_end = abs_end - len(close_tag)
        old_body = html_content[tag_end:body_end]
        if old_body != new_body:
            ops.append((tag_end, body_end, new_body))

    # Sort descending by start position so right-to-left splice keeps offsets valid
    ops.sort(key=lambda x: x[0], reverse=True)
    for (start, end, new_body) in ops:
        html_content = html_content[:start] + new_body + html_content[end:]

    return html_content


def _fast_search(pattern_str, haystack):
    """
    Fast two-phase search against a large HTML string.

    Phase A: literal str.find() -- O(n) with no backtracking, ~100x faster
             than a compiled regex on a 16 MB string.  Used when the anchor
             contains no regex metacharacters after the s*-n-s* expansion.
    Phase B: compiled regex fallback -- only reached when the literal search
             fails (anchor absent) or when the pattern contains active regex
             syntax beyond the whitespace-flexible newline substitution.

    Returns a re.Match-compatible object (or None).
    """
    # Reconstruct the literal form: pattern_str was built by
    #   re.escape(anchor).replace(r'\n', r'\s*\n\s*')
    # Reverse: strip the whitespace-flexible newline padding back to a plain
    # literal so we can try str.find() first.
    literal = pattern_str.replace(r'\s*\n\s*', '\n').replace(r'\s*\n', '\n').replace(r'\n\s*', '\n')
    # Only use the fast path when the result is a plain literal -- re.escape
    # already neutralized all metacharacters, so the only remaining active
    # syntax was the whitespace-flexible newline substitution.
    # Strip the outer capture group parens added by the caller.
    inner = literal
    if inner.startswith('(') and inner.endswith(')'):
        inner = inner[1:-1]
    pos = haystack.find(inner)
    if pos != -1:
        # Literal hit -- wrap in a minimal match-like object so callers can
        # use .start(), .end(), and .group() without changes.
        class _LiteralMatch:
            __slots__ = ('_s', '_e', '_text')
            def __init__(self, s, e, text):
                self._s = s; self._e = e; self._text = text
            def start(self, g=0): return self._s
            def end(self,   g=0): return self._e
            def group(self, g=0): return self._text
        return _LiteralMatch(pos, pos + len(inner), inner)
    # Fast path missed -- fall back to compiled regex (handles genuine
    # whitespace variation between anchor lines).
    return _get_compiled(pattern_str).search(haystack)


def patch_html_file(html_file, mod_dict, mod_list, mod_file_indexes, mod_reg_list, mod_struct_list, mod_func_list, mod_hook_list, conflict_map, loaded_mod_files=None, passage_registry=None, passage_names_seen=None, js_registry=None, css_registry=None, events_registry=None, key_to_mod=None):

    successful_mods = []
    failed_mods = []
    # Run duplicate checks before injection
    _dup_warnings = _check_mod_duplicates(mod_dict, mod_func_list, mod_file_indexes, js_registry=js_registry, events_registry=events_registry)
    dup_warned_mods = set()
    for _msg, _is_err in _dup_warnings:
        handle_output(_msg, "log")
        if _is_err:
            handle_output(_msg, "failed")
            # Extract mod names from dup warning messages for Warned Mods list
            for _lmf in (loaded_mod_files or []):
                if os.path.basename(_lmf) in _msg:
                    dup_warned_mods.add(os.path.basename(_lmf))
    # Duplicate warnings go to FailsPatchLog via the "failed" log channel above.
    # Do NOT add all loaded mods to failed_mods -- only real directive failures
    # belong in failed_mods.


    _log_buffer['main'].clear()
    _log_buffer['mod'].clear()
    _log_buffer['failed'].clear()
    clear_logs()
    with open(log_file, 'w', encoding='utf-8') as log:
        log.write("Mod patching started...\n")

    if not os.path.exists(html_file):
        handle_output(f"Error: HTML file '{html_file}' not found.", "log")
        if running_from_cli():
            input("Press Enter to exit...")
        sys.exit(1)

    with open(html_file, 'r', encoding='utf-8') as file:
        html_content = file.read()
    # Normalize Windows CRLF to LF so all matching works uniformly
    html_content = html_content.replace('\r\n', '\n').replace('\r', '\n')

    # ---- v0.7.0: KittyHTMLLayer (BS4 DOM layer) ----
    # Used for structural ops: Delete Block, Rename Passage, Add/Remove Tag,
    # Add Passage injection, PID renormalization, and final serialize.
    # All text-search directives (Insert After, Replace In Passage, etc.)
    # continue to operate on the raw html_content string.
    _html_layer = KittyHTMLLayer(html_content)

    # Already-patched watermark check (advisory warning only)
    _existing_watermark = _html_layer.get_watermark()
    if _existing_watermark:
        handle_output(
            f"WARNING: this HTML was previously patched by KittyPatcher {_existing_watermark} -- "
            f"patching the original CourseOfTemptation.html is recommended",
            "alllogs"
        )

    # Storydata metadata log (v0.7.0 section 1.7)
    _sd_attrs = _html_layer.get_storydata_attrs()
    if _sd_attrs:
        handle_output(
            f"Game: {_sd_attrs.get('name', '?')}  "
            f"creator-version: {_sd_attrs.get('creator-version', '?')}  "
            f"ifid: {_sd_attrs.get('ifid', '?')}",
            "alllogs"
        )

    # ---- v0.7.0: Passage validation at load time (Plan 1.6) ----
    if _html_layer.bs4_available:
        _seen_pids = {}
        for _vtag in _html_layer._soup.find_all("tw-passagedata"):
            _vname = _vtag.get("name")
            _vpid  = _vtag.get("pid", "")
            if not _vname:
                handle_output(
                    f"MALFORMED PASSAGE: missing name attribute (pid={_vpid!r})",
                    "alllogs"
                )
            if _vpid:
                if _vpid in _seen_pids:
                    handle_output(
                        f"MALFORMED PASSAGE: duplicate pid={_vpid!r} (passages '{_seen_pids[_vpid]}' and '{_vname or '?'}')",
                        "alllogs"
                    )
                else:
                    _seen_pids[_vpid] = _vname or "?"

    # ---- Pid generator setup ----
    # v0.7.2 Option 1: build passage dict for O(1) per-passage access.
    # _split_html also computes max_pid during the same scan so _get_max_pid
    # does not need a separate re.findall pass over the full 20MB HTML.
    _passage_dict, _passage_meta, _script_block, _max_pid = _split_html(html_content)
    # _passage_dict[name] = body string (encoded, as-in-HTML)
    # Used by all passage-scoped Phase 1 and Phase 4 handlers.

    _next_pid = _max_pid + 1
    _detect_pid_collisions(mod_dict, html_content, passage_registry=passage_registry, passage_meta=_passage_meta)

    replacements_made = 0
    replacements_failed = 0
    _replacements_resolved = 0  # incremented when Phase 6/7 sweeps retroactively resolve a failure
    _failed_replace_keys = set()
    _failed_ia_ib_entries = []

    # ---- Snapshot vanilla passage names for duplicate checking ----
    # Used by Add Passage registry injection (Phase 7) to skip passages that
    # already exist in the vanilla HTML.  Delete Block removes names from this
    # set so a subsequent Add Passage for the same name is not skipped.
    # v0.7.2: passage dict already has all names
    _original_passage_names = set(_passage_dict.keys())
    # Clear stale DiffAssist port drafts when KittyDiffAssist is present.
    if _DIFFASSIST_AVAILABLE:
        _KittyDiffAssist.clear(logs_folder)


    # ---- v0.7.0: Anchor normalization helper ----
    # Modders may write anchors in decoded Twine syntax (<<if $x>>) or in
    # HTML-escaped form (&lt;&lt;if $x&gt;&gt;).  _normalize_anchor converts
    # decoded syntax to escaped form so it matches the HTML.  Already-escaped
    # anchors pass through unchanged (escape_twine_tags is idempotent).
    def _normalize_anchor(anchor):
        return escape_twine_tags(anchor)

    # v0.7.4: raw anchor for script-block fallback -- escape_twine_tags encodes
    # quotes to &quot; which breaks Replace: anchors targeting JS object entries
    # in the script block (e.g. entries in setup.storyhints.db).  Script block
    # content stores raw " not &quot;.  The two-pass approach below tries the
    # encoded anchor first (correct for passage content) and falls back to the
    # raw anchor when the encoded search misses and the anchor has no passage tag.
    def _raw_anchor(anchor):
        return anchor

    # ---- Classic Replace: entries ----
    # v0.6.0: Collect passage-targeting replacements for two-phase reverse-offset
    # application (Part E Option C).  Non-passage entries use the existing regex path.
    _passage_replacements = []  # list of (name, new_content, old_lines, guards, entry)

    # v0.7.2: collect (match_pos, mod_label) for batch tag balance check
    # after Phase 1 completes instead of running inline per-replacement.
    _deferred_balance_checks = []

    for _ml_old_key, _ml_source_mod in mod_list:
        # v0.7.6: look up live entry from mod_dict -- inner-replacement may have
        # mutated the With: body since this entry was appended to mod_list.
        # If the key was consumed by inner-replacement (pop'd from mod_dict), skip.
        if _ml_old_key not in mod_dict:
            continue
        old_lines = _ml_old_key
        entry     = mod_dict[_ml_old_key]

        # v0.6.0: All entries are now (text, guards) tuples -- no more plain string accumulators
        new_lines, guards = entry

        # Evaluate guard clauses
        if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
            handle_output(f"Guard condition not met for '{old_lines}', skipping.", "log")
            continue

        # Expand [to] marker
        old_lines = update_old_lines_from_html(old_lines, html_content)
        # v0.7.0: normalize anchor -- modders may write <<macros>> or &lt;&lt;macros&gt;&gt;
        # v0.7.4: two-pass -- try encoded anchor first (correct for passage content),
        # then fall back to raw anchor if that misses and target has no passage tag
        # (script block targets store raw " not &quot; so encoding breaks them).
        _old_lines_raw  = _raw_anchor(old_lines)
        old_lines       = _normalize_anchor(old_lines)
        # v0.7.5: resolve pid="auto" / position="auto" (and their &quot; encoded forms
        # produced by EscapeTwineTags on legacy ~~ entries) in the anchor itself,
        # not just in the With: body.  This lets ~~ delimiter blocks use pid="auto"
        # and position="auto" exactly like new-style Replace: directives do.
        old_lines       = _resolve_pid_auto_in_anchor(old_lines, html_content)
        _old_lines_raw  = _resolve_pid_auto_in_anchor(_old_lines_raw, html_content)

        # Safer newline matching
        old_lines_pattern = re.escape(old_lines).replace(r'\n', r'\s*\n\s*')
        pattern = rf'({old_lines_pattern})'

        # Extract passage name from Replace: target once, shared by both match and fallback paths
        passage_name_m = re.search(r'<tw-passagedata[^>]*name="([^"]+)"', old_lines)

        # v0.7.2 Option 1: if the Replace: target is passage-opening-tag-based AND
        # the passage body is in the dict, search only that body (avg 3.5 KB vs 20 MB).
        # For script-targeted and non-passage anchors fall back to full string.
        # v0.7.2 fix: boundary-crossing anchors contain content BEFORE the
        # <tw-passagedata tag (e.g. the closing line of the previous passage).
        # These must always use full-string search -- the pre-tag content is not
        # part of the named passage's body dict entry and the scoped search would
        # miss it, causing the Replace to silently fail.
        _p1_passage_name = passage_name_m.group(1) if passage_name_m else None
        _p1_is_boundary_cross = bool(
            passage_name_m and old_lines[:passage_name_m.start()].strip()
        )
        if _p1_passage_name and _p1_passage_name in _passage_dict and not _p1_is_boundary_cross:
            # Passage-dict fast path: build a synthetic searchable string that
            # includes the opening tag so the Replace: target (which may contain
            # the full <tw-passagedata ...> tag) can still match.
            _p1_meta = _passage_meta.get(_p1_passage_name)
            if _p1_meta:
                _p1_open_tag, _p1_abs_start, _p1_abs_end = _p1_meta
                _p1_slice = _p1_open_tag + _passage_dict[_p1_passage_name] + '</tw-passagedata>'
                match = _fast_search(pattern, _p1_slice)
                if match:
                    # Remap match position to absolute html_content coordinates
                    # so downstream rfind() context detection works correctly.
                    _p1_offset = _p1_abs_start
                    class _RemappedMatch:
                        __slots__ = ('_m', '_off')
                        def __init__(self, m, off): self._m = m; self._off = off
                        def start(self, g=0): return self._m.start(g) + self._off
                        def end(self,   g=0): return self._m.end(g)   + self._off
                        def group(self, g=0): return self._m.group(g)
                    match = _RemappedMatch(match, _p1_offset)
                else:
                    match = None
            else:
                match = _fast_search(pattern, html_content)
        else:
            # Non-passage or script-block anchor -- search full string
            match = _fast_search(pattern, html_content)

        # ---- v0.7.4: Raw anchor fallback for script-block Replace: targets ----
        # If the encoded anchor missed and the anchor has no passage tag (i.e. it
        # targets script block content rather than passage content), retry with the
        # raw unencoded anchor.  Script block stores raw " not &quot;, so Replace:
        # on JS object entries like setup.storyhints.db entries fails with the
        # encoded anchor.  Only fires when: (a) match failed, (b) no passage tag
        # in anchor (passage targets should stay encoded), (c) encoded and raw
        # anchors differ (if they're the same the retry is pointless).
        if not match and not passage_name_m and _old_lines_raw != old_lines:
            _raw_pattern = rf'({re.escape(_old_lines_raw).replace(r"\n", r"\s*\n\s*")})'
            match_raw = _fast_search(_raw_pattern, html_content)
            if match_raw:
                handle_output(
                    f"Replace: encoded anchor missed -- raw script-block fallback "
                    f"succeeded for '{old_lines[:80].strip()}...' (v0.7.4)", "log"
                )
                # Switch to raw anchor and pattern for downstream apply
                old_lines = _old_lines_raw
                pattern   = _raw_pattern
                match     = match_raw

        # ---- Live-pid retry for pid="auto" in Replace: target (v0.5.3) ----
        # If the initial exact match failed and the target contains pid="auto",
        # look up the live pid of the named passage from the current HTML and
        # substitute it into old_lines before retrying.  This lets the exact
        # match path succeed even when the mod never hardcoded a pid, while
        # still falling through to the name-based fallback if the rest of the
        # opening tag or first line has also drifted.
        if not match and passage_name_m and 'pid="auto"' in old_lines.lower():
            _retry_pname = passage_name_m.group(1)
            _live_tag_m = re.search(
                r'<tw-passagedata[^>]*name="' + re.escape(_retry_pname) + r'"[^>]*>',
                html_content
            )
            if _live_tag_m:
                _live_pid_m = re.search(r'pid="([^"]+)"', _live_tag_m.group(0))
                if _live_pid_m:
                    _live_pid = _live_pid_m.group(1)
                    old_lines_retried = re.sub(
                        r'pid="auto"', f'pid="{_live_pid}"', old_lines,
                        count=1, flags=re.IGNORECASE
                    )
                    old_lines_pattern_retried = re.escape(old_lines_retried).replace(r'\n', r'\s*\n\s*')
                    pattern_retried = rf'({old_lines_pattern_retried})'
                    match_retried = _fast_search(pattern_retried, html_content)
                    if match_retried:
                        # Retry succeeded -- use the corrected old_lines and pattern
                        old_lines = old_lines_retried
                        pattern   = pattern_retried
                        match     = match_retried
                        handle_output(
                            f"Replace: pid=\"auto\" resolved to pid=\"{_live_pid}\" "
                            f"for '{_retry_pname}' -- exact match succeeded.", "log"
                        )
                    else:
                        handle_output(
                            f"Replace: pid=\"auto\" resolved to pid=\"{_live_pid}\" "
                            f"for '{_retry_pname}' -- retried exact match also failed, "
                            f"falling back to name-based match.", "log"
                        )

        if match:

            # Resolve pid="auto" placeholders in the replacement text.
            if 'pid="auto"' in new_lines or 'pid="AUTO"' in new_lines:
                new_lines, _next_pid = _resolve_auto_pids(new_lines, _next_pid)

            # Determine if the match is inside a raw <script> block.
            # If so, unescape &lt;&lt; back to << before injecting.
            apply_lines = new_lines

            # Resolve pid="auto" / position="auto" in the With: body (v0.5.3).
            # Must run before script-context unescape so attribute values are
            # always written as plain strings, never as HTML entities.
            if passage_name_m and ('<tw-passagedata' in apply_lines):
                _auto_pname = passage_name_m.group(1) if passage_name_m else None
                if _auto_pname and ('pid="auto"' in apply_lines or 'position="auto"' in apply_lines):
                    apply_lines = _resolve_auto_passage_attrs(apply_lines, html_content, _auto_pname)

            match_pos = match.start()
            last_script       = html_content.rfind('</style><script',   0, match_pos)
            last_passage_open = html_content.rfind('<tw-passagedata',    0, match_pos)
            last_passage_close= html_content.rfind('</tw-passagedata>', 0, match_pos)
            if (last_script != -1 and
                    last_script > last_passage_open and
                    last_script > last_passage_close):
                # Only unescape when the Replace: target itself uses raw syntax
                # (no HTML entities). If the target contains &lt; or &gt;, the
                # matched content is HTML-escaped passage data stored inside the
                # script block, not raw JS -- the With: body must stay escaped.
                if '&lt;' not in old_lines and '&gt;' not in old_lines:
                    apply_lines = apply_lines.replace('&lt;&lt;', '<<').replace('&gt;&gt;', '>>').replace('&gt;', '>').replace('&lt;', '<').replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'")

            # Prevent duplicate patching: skip past any prefix shared with old_lines
            # so we only probe content unique to the With: body. This avoids false
            # positives when the body starts with the same text as the target (e.g.
            # function replacements that keep the signature), and avoids the old
            # window-size false positive that affected massive replacements.
            new_stripped = apply_lines.strip()
            old_stripped = old_lines.strip()
            # Find how many leading chars new and old share
            overlap = 0
            for i in range(min(len(old_stripped), len(new_stripped))):
                if new_stripped[i] == old_stripped[i]:
                    overlap = i + 1
                else:
                    break
            # Probe is the unique suffix of the new body after the shared prefix.
            # Check only in the region immediately following the match end.
            probe = new_stripped[overlap:]
            if probe:
                check_start = match.end()
                check_end   = check_start + len(probe) + 200
                if probe in html_content[check_start:check_end]:
                    handle_output(f"Patch already applied at match site for '{old_lines}', skipping.", "log")
                    continue

            # Change 1: When match is inside a passage body (not script block),
            # auto-escape any raw <<macros>> in the With: body the modder wrote.
            # escape_twine_tags is idempotent -- already-escaped bodies pass through.
            # This lets modders write <<if $x>> instead of &lt;&lt;if $x&gt;&gt;
            # in With: bodies targeting passage content.
            # Downside: tiny extra pass over the With: body string. Cost is O(B)
            # where B = With: body length -- negligible vs the regex match above.
            # Only fires when match is in a passage body AND body contains raw macros.
            _in_passage_ctx = (
                last_passage_open != -1 and
                last_passage_open > last_script and
                last_passage_open > last_passage_close
            )
            if _in_passage_ctx and ('<<' in apply_lines or '>>' in apply_lines):
                apply_lines = escape_twine_tags(apply_lines)

            if _verbose_logging:
                handle_output(f"Replacing '{old_lines}' with '{apply_lines}'", "log")
            else:
                # Concise: just log that a replacement was made, with a short preview
                _preview = old_lines[:80].replace('\n', ' ')
                handle_output(f"Replaced: '{_preview}'", "log")

            # Use count=0 (replace all occurrences) only when the match is inside
            # the raw script block -- repeated JS patterns like archetype tables
            # must all be updated. For passage content, use count=1 so a single-
            # passage anchor is not applied to every other passage that shares it.
            _resub_count = 0 if (last_script != -1 and
                                  last_script > last_passage_open and
                                  last_script > last_passage_close) else 1
            # Use lambda to prevent re.sub interpreting \1, \g<0> etc.
            # in mod replacement text as backreferences.
            html_content = re.sub(pattern, lambda _m: apply_lines, html_content, count=_resub_count)

            # v0.7.2: defer tag balance checks to a batch run after Phase 1 completes.
            # Attribution is preserved by recording (match_pos, mod_label) here and
            # running check_injection_tag_balance once per entry after the loop.
            # This avoids calling the checker inline on a 20MB string for every
            # successful replacement -- the checker runs against the final post-Phase-1
            # html_content which is slightly different but the passage location is the same.
            _mod_label = key_to_mod.get(old_lines, 'unknown') if key_to_mod else 'unknown'
            _deferred_balance_checks.append((match_pos, _mod_label))

            replacements_made += 1

            # O(1) mod source lookup via key_to_mod (already used above for _mod_label)
            if _mod_label != 'unknown':
                successful_mods.append(_mod_label)
            else:
                for key, value in mod_file_indexes.items():
                    if old_lines in value:
                        successful_mods.append(key)

        else:

            # If the target is a passage tag, run pid-aware diagnostics then fall back
            # to name-based replacement.
            passage_name_m = re.search(r'<tw-passagedata[^>]*name="([^"]+)"', old_lines)
            mod_pid_m      = re.search(r'<tw-passagedata[^>]*pid="([^"]+)"',  old_lines)

            if passage_name_m and mod_pid_m:
                pname   = passage_name_m.group(1)
                mod_pid = mod_pid_m.group(1)

                # ---- Pid-aware diagnostic step (v0.5.0) ----
                # Skip entirely when mod uses pid="auto" -- mod author is explicitly
                # requesting name-based match, no diagnostic needed (v0.5.3).
                if mod_pid.lower() == 'auto':
                    handle_output(
                        f"Replace: pid=\"auto\" for '{pname}' -- using name-based match.", "log"
                    )
                else:
                    game_tag_m = re.search(
                        r'<tw-passagedata[^>]*pid="' + re.escape(mod_pid) + r'"[^>]*>',
                        html_content
                    )
                    if game_tag_m:
                        game_name_m = re.search(r'name="([^"]+)"', game_tag_m.group(0))
                        game_name   = game_name_m.group(1) if game_name_m else '(unknown)'
                        if game_name == pname:
                            # Same passage at same pid -- opening tag attributes changed
                            _log_opening_tag_diff(old_lines, game_tag_m.group(0), pname, mod_pid)
                        else:
                            # Pid belongs to a different passage -- collision or reorganisation
                            handle_output(
                                f"PID MISMATCH: mod targets '{pname}' with pid={mod_pid} "
                                f"but game's pid={mod_pid} belongs to '{game_name}'. "
                                f"Falling back to name-based match.", "log"
                            )
                    else:
                        # Pid not present in game at all -- renormalised or reorganised
                        handle_output(
                            f"PID NOT FOUND: pid={mod_pid} (passage '{pname}') "
                            f"not present in current HTML. Game may have renormalised pids. "
                            f"Falling back to name-based match.", "log"
                        )

            # ---- Name-based fallback (v0.5.0: smart partial-vs-full replace) ----
            if passage_name_m:
                pname = passage_name_m.group(1)
                # apply_lines is only set inside the if match: branch above.
                # Assign it here so the name-based path always uses the correct With: body.
                apply_lines = new_lines
                passage_pat = _get_compiled(
                    r'<tw-passagedata[^>]*name="' + re.escape(pname) + r'"[^>]*>.*?</tw-passagedata>',
                    re.DOTALL
                )
                pm = passage_pat.search(html_content)
                if pm:
                    # Resolve pid="auto" / position="auto" before writing (v0.5.3).
                    # pm gives us the live opening tag directly.
                    if 'pid="auto"' in apply_lines or 'position="auto"' in apply_lines:
                        apply_lines = _resolve_auto_passage_attrs(apply_lines, html_content, pname)

                    if '</tw-passagedata>' in apply_lines:
                        # With: body is a complete passage -- full replacement
                        html_content = html_content[:pm.start()] + apply_lines + html_content[pm.end():]
                        handle_output(f"Replaced passage '{pname}' by name (full replacement)", "log")
                    else:
                        # With: body is an opening tag only -- preserve original body and close
                        open_tag_end = html_content.index('>', pm.start()) + 1
                        html_content = html_content[:pm.start()] + apply_lines.strip() + html_content[open_tag_end:]
                        handle_output(f"Replaced opening tag of '{pname}' by name (tag-only update)", "log")
                    replacements_made += 1
                    for key, value in mod_file_indexes.items():
                        if old_lines in value:
                            successful_mods.append(key)
                    continue

            handle_output(f"No match found for '{old_lines}'", "log")
            handle_output(f"No match found for '{old_lines}'", "failed")
            _failed_replace_keys.add(old_lines)


            replacements_failed += 1

            for key, value in mod_file_indexes.items():
                if old_lines in value:
                    failed_mods.append(key)

    # v0.7.2 Option 1: Phase 1 may have mutated html_content -- rebuild passage_dict
    # so Phase 4 sees all Phase 1 changes when doing passage-scoped lookups.
    _passage_dict, _passage_meta, _script_block, _max_pid = _split_html(html_content)

    # v0.7.2 fix3: run deferred tag balance checks in one batch after Phase 1.
    # Each check carries its original mod_label for accurate attribution.
    for _bpos, _blabel in _deferred_balance_checks:
        for _bw in check_injection_tag_balance(html_content, _bpos, _blabel):
            handle_output(_bw, 'alllogs')
    _deferred_balance_checks.clear()

    flush_logs()
    # ---- ReplaceReg entries ----
    for entry in mod_reg_list:
        pat      = entry['pattern']
        groups   = entry['groups']    # list of (group_index, replacement_text)
        guards   = entry['guards']
        mod_file = entry['mod_file']
        entry_key = f'ReplaceReg [{pat}]'

        # Evaluate guard clauses
        if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
            handle_output(f"Guard condition not met for '{entry_key}', skipping.", "log")
            continue

        try:
            compiled = _get_compiled(pat, re.DOTALL)
        except re.error as e:
            handle_output(f"Invalid regex in '{entry_key}': {e}", "log")
            handle_output(f"Invalid regex in '{entry_key}': {e}", "failed")
            replacements_failed += 1
            failed_mods.append(mod_file)
            continue

        match = compiled.search(html_content)
        if not match:
            handle_output(f"No match found for '{entry_key}'", "log")
            handle_output(f"No match found for '{entry_key}'", "failed")
            replacements_failed += 1
            failed_mods.append(mod_file)
            continue

        # Resolve each group's span. Group 0 = whole match; groups 1+ = capture groups.
        # Collect ops then sort descending by start offset so right-to-left splicing
        # keeps earlier offsets valid after each edit.
        group_ops = []
        valid = True
        for (gidx, repl_text) in groups:
            try:
                gstart, gend = match.span(gidx)
            except IndexError:
                handle_output(f"Group {gidx} does not exist in pattern '{pat}'", "log")
                handle_output(f"Group {gidx} does not exist in pattern '{pat}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                valid = False
                break
            group_ops.append((gstart, gend, repl_text))

        if not valid:
            continue

        # Duplicate-patch check: use a local window around each group span, not global search
        def _already_applied(gstart, gend, rt):
            window_start = max(0, gstart - len(rt))
            window_end   = min(len(html_content), gend + len(rt))
            return rt in html_content[window_start:window_end]

        if all(_already_applied(gs, ge, rt) for gs, ge, rt in group_ops):
            handle_output("Patch already applied, skipping.", "log")
            continue

        group_ops.sort(key=lambda x: x[0], reverse=True)
        for (gstart, gend, repl_text) in group_ops:
            handle_output(f"ReplaceReg group span [{gstart}:{gend}] with '{repl_text}'", "log")
            html_content = html_content[:gstart] + repl_text + html_content[gend:]

        replacements_made += 1
        successful_mods.append(mod_file)

    # ---- Append Array / Append Variable to Class / Append Function to Class ----

    def _bracket_match(text, open_pos, open_ch, close_ch):
        """
        Starting from open_pos (which must be the index of open_ch), walk forward
        tracking nesting depth.  Returns the index of the matching close_ch, or -1.
        Skips over single-quoted, double-quoted, and template-literal strings, and
        line/block comments, so bracket characters inside strings do not count.
        """
        depth = 0
        i = open_pos
        n = len(text)
        while i < n:
            ch = text[i]
            # Skip line comment
            if ch == '/' and i + 1 < n and text[i + 1] == '/':
                i = text.find('\n', i)
                if i == -1:
                    return -1
                continue
            # Skip block comment
            if ch == '/' and i + 1 < n and text[i + 1] == '*':
                i = text.find('*/', i + 2)
                if i == -1:
                    return -1
                i += 2
                continue
            # Skip string literals
            if ch in ('"', "'", '`'):
                quote = ch
                i += 1
                while i < n:
                    c = text[i]
                    if c == '\\':
                        i += 2
                        continue
                    if c == quote:
                        break
                    i += 1
                i += 1
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    for entry in mod_struct_list:
        kind     = entry['kind']
        name     = entry['name']
        content  = entry['content']
        mod_file = entry['mod_file']
        entry_key = f'{kind} [{name}]'
        guards = entry.get('guards', {})
        if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
            handle_output(f"Guard condition not met for '{entry_key}', skipping.", "log")
            continue

        if kind == 'append_array':
            # Find:  name = [  or  name: [  or  name=[  anywhere in the HTML.
            # Searches all occurrences to support local variables, object fields,
            # and top-level assignments (v0.5.0: extended from top-level only).
            pat = re.escape(name) + r'\s*[=:]\s*\['
            matches_all = list(re.finditer(pat, html_content))
            if not matches_all:
                handle_output(f"No match found for '{entry_key}'", "log")
                handle_output(f"No match found for '{entry_key}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            # Duplicate check: content already present anywhere in HTML
            if content in html_content:
                handle_output(f"Patch already applied for '{entry_key}', skipping.", "log")
                continue
            # Apply to ALL matching occurrences so repeated patterns (e.g. per-ethnicity
            # archetype tables) are all updated, not just the first.
            # Process right-to-left so earlier offsets stay valid after each edit.
            applied = 0
            for m in reversed(matches_all):
                open_pos = html_content.index('[', m.start())
                close_pos = _bracket_match(html_content, open_pos, '[', ']')
                if close_pos == -1:
                    continue
                insertion = '\n' + content + '\n'
                html_content = html_content[:close_pos] + insertion + html_content[close_pos:]
                applied += 1
            if applied:
                handle_output(f"Appended to array '{name}' ({applied} occurrence(s))", "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                handle_output(f"Could not find closing ] for '{entry_key}'", "log")
                handle_output(f"Could not find closing ] for '{entry_key}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)

        elif kind == 'append_var':
            # Find the constructor of the class or the function body (prototype class).
            # Try class syntax first: class Name { constructor( ... ) { ... } }
            # Fall back to: function Name( ... ) { ... }
            constructor_pat = _get_compiled(
                r'class\s+' + re.escape(name) + r'\b[^{]*\{',
                re.DOTALL
            )
            cm = constructor_pat.search(html_content)
            if cm:
                # Found class body opening -- now find constructor( inside class body
                class_open = html_content.index('{', cm.start())
                class_close = _bracket_match(html_content, class_open, '{', '}')
                if class_close == -1:
                    handle_output(f"Could not find class body end for '{entry_key}'", "log")
                    handle_output(f"Could not find class body end for '{entry_key}'", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                class_body = html_content[class_open:class_close + 1]
                ctor_m = re.search(r'\bconstructor\s*\(', class_body)
                if ctor_m:
                    ctor_open_rel = class_body.index('(', ctor_m.start())
                    # skip past the parameter list to the {
                    paren_close = _bracket_match(class_body, ctor_open_rel, '(', ')')
                    if paren_close == -1:
                        handle_output(f"Could not match constructor params for '{entry_key}'", "log")
                        replacements_failed += 1
                        failed_mods.append(mod_file)
                        continue
                    brace_start_rel = class_body.index('{', paren_close)
                    brace_end_rel = _bracket_match(class_body, brace_start_rel, '{', '}')
                    if brace_end_rel == -1:
                        handle_output(f"Could not match constructor body for '{entry_key}'", "log")
                        replacements_failed += 1
                        failed_mods.append(mod_file)
                        continue
                    insert_pos = class_open + brace_end_rel
                else:
                    handle_output(f"No constructor found in class '{name}' for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
            else:
                # Try prototype-style: function Name(
                func_m = re.search(r'function\s+' + re.escape(name) + r'\s*\(', html_content)
                if not func_m:
                    handle_output(f"No match found for '{entry_key}'", "log")
                    handle_output(f"No match found for '{entry_key}'", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                paren_open = html_content.index('(', func_m.start())
                paren_close = _bracket_match(html_content, paren_open, '(', ')')
                if paren_close == -1:
                    handle_output(f"Could not match param list for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                brace_open = html_content.find('{', paren_close)
                if brace_open == -1:
                    handle_output(f"Could not find opening brace for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                brace_close = _bracket_match(html_content, brace_open, '{', '}')
                if brace_close == -1:
                    handle_output(f"Could not match function body for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                insert_pos = brace_close

            if content in html_content:
                handle_output(f"Patch already applied for '{entry_key}', skipping.", "log")
                continue
            insertion = '\n    ' + content + '\n'
            html_content = html_content[:insert_pos] + insertion + html_content[insert_pos:]
            handle_output(f"Appended variable to class/function '{name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'append_func':
            # Find end of class body and insert method before closing }
            # Supports class syntax and prototype-style (inserts after function body as MyClass.prototype.X)
            class_m = re.search(r'class\s+' + re.escape(name) + r'\b[^{]*\{', html_content, re.DOTALL)
            if class_m:
                class_open = html_content.index('{', class_m.start())
                class_close = _bracket_match(html_content, class_open, '{', '}')
                if class_close == -1:
                    handle_output(f"Could not find class body end for '{entry_key}'", "log")
                    handle_output(f"Could not find class body end for '{entry_key}'", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                insert_pos = class_close
                if content in html_content:
                    handle_output(f"Patch already applied for '{entry_key}', skipping.", "log")
                    continue
                # Indent each line of the method body by 4 spaces
                indented = '\n'.join('    ' + ln if ln.strip() else ln for ln in content.splitlines())
                insertion = '\n' + indented + '\n'
                html_content = html_content[:insert_pos] + insertion + html_content[insert_pos:]
                handle_output(f"Appended function to class '{name}'", "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                # Prototype-style: find function body end, insert MyClass.prototype.method after it
                func_m = re.search(r'function\s+' + re.escape(name) + r'\s*\(', html_content)
                if not func_m:
                    handle_output(f"No match found for '{entry_key}'", "log")
                    handle_output(f"No match found for '{entry_key}'", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                paren_open = html_content.index('(', func_m.start())
                paren_close = _bracket_match(html_content, paren_open, '(', ')')
                if paren_close == -1:
                    handle_output(f"Could not match param list for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                brace_open = html_content.find('{', paren_close)
                if brace_open == -1:
                    handle_output(f"Could not find opening brace for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                brace_close = _bracket_match(html_content, brace_open, '{', '}')
                if brace_close == -1:
                    handle_output(f"Could not match function body for '{entry_key}'", "log")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                if content in html_content:
                    handle_output(f"Patch already applied for '{entry_key}', skipping.", "log")
                    continue
                # Wrap content as prototype assignment(s)
                # content is expected to be:  methodName() { ... }  or  methodName: function() { ... }
                # We wrap it as: ClassName.prototype.methodName = function(...) { ... };
                insertion = f'\n{name}.prototype.' + content.rstrip() + '\n'
                html_content = html_content[:brace_close + 1] + insertion + html_content[brace_close + 1:]
                handle_output(f"Appended prototype function to '{name}'", "log")
                replacements_made += 1
                successful_mods.append(mod_file)
        elif kind == 'insert_into_array':
            # Find an array by name anywhere in scope (local var, top-level, object field)
            # and inject entries before its closing ].
            # If scope_func is set, restrict matches to inside that function body only.
            scope_func = entry.get('scope_func')
            search_space = html_content
            offset = 0
            if scope_func:
                sf_pat = _get_compiled(
                    r'(' + re.escape(scope_func) + r'\s*[=:]\s*function\s*\(.*?\)\s*\{'
                    r'|function\s+' + re.escape(scope_func) + r'\s*\(.*?\)\s*\{)',
                    re.DOTALL
                )
                sf_m = sf_pat.search(html_content)
                if sf_m:
                    sf_brace = html_content.rindex('{', sf_m.start(), sf_m.end())
                    sf_end = _bracket_match(html_content, sf_brace, '{', '}')
                    if sf_end != -1:
                        offset = sf_brace
                        search_space = html_content[sf_brace:sf_end + 1]
                    else:
                        handle_output(f"Insert Into Array: could not find body of scope function '{scope_func}'", "log")
                else:
                    handle_output(f"Insert Into Array: scope function '{scope_func}' not found, searching globally", "log")
            pat = re.escape(name) + r'\s*[=:]\s*\['
            matches_all = list(re.finditer(pat, search_space))
            if not matches_all:
                handle_output(f"Insert Into Array: no match for '{name}'" + (f" in '{scope_func}'" if scope_func else ""), "log")
                handle_output(f"Insert Into Array: no match for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            if content in search_space:
                handle_output(f"Insert Into Array: already applied for '{name}', skipping.", "log")
                continue
            applied = 0
            for m in reversed(matches_all):
                abs_start = offset + m.start()
                open_pos = html_content.find('[', abs_start)
                if open_pos == -1:
                    continue
                close_pos = _bracket_match(html_content, open_pos, '[', ']')
                if close_pos == -1:
                    continue
                insertion = '\n' + content + '\n'
                html_content = html_content[:close_pos] + insertion + html_content[close_pos:]
                applied += 1
            if applied:
                handle_output(f"Insert Into Array: inserted into '{name}' ({applied} occurrence(s))" + (f" in '{scope_func}'" if scope_func else ""), "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                handle_output(f"Insert Into Array: could not find closing ] for '{name}'", "log")
                handle_output(f"Insert Into Array: could not find closing ] for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)

        elif kind == 'insert_into_object':
            # Find an object literal by name anywhere in scope and inject new key:value
            # pairs before its closing }.
            # If scope_func is set, restrict matches to inside that function body only.
            scope_func = entry.get('scope_func')
            search_space = html_content
            offset = 0
            if scope_func:
                sf_pat = _get_compiled(
                    r'(' + re.escape(scope_func) + r'\s*[=:]\s*function\s*\(.*?\)\s*\{'
                    r'|function\s+' + re.escape(scope_func) + r'\s*\(.*?\)\s*\{)',
                    re.DOTALL
                )
                sf_m = sf_pat.search(html_content)
                if sf_m:
                    sf_brace = html_content.rindex('{', sf_m.start(), sf_m.end())
                    sf_end = _bracket_match(html_content, sf_brace, '{', '}')
                    if sf_end != -1:
                        offset = sf_brace
                        search_space = html_content[sf_brace:sf_end + 1]
                    else:
                        handle_output(f"Insert Into Object: could not find body of scope function '{scope_func}'", "log")
                else:
                    handle_output(f"Insert Into Object: scope function '{scope_func}' not found, searching globally", "log")
            pat = re.escape(name) + r'\s*[=:]\s*\{'
            matches_all = list(re.finditer(pat, search_space))
            if not matches_all:
                handle_output(f"Insert Into Object: no match for '{name}'" + (f" in '{scope_func}'" if scope_func else ""), "log")
                handle_output(f"Insert Into Object: no match for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            if content in search_space:
                handle_output(f"Insert Into Object: already applied for '{name}', skipping.", "log")
                continue
            applied = 0
            for m in reversed(matches_all):
                abs_start = offset + m.start()
                open_pos = html_content.find('{', abs_start)
                if open_pos == -1:
                    continue
                close_pos = _bracket_match(html_content, open_pos, '{', '}')
                if close_pos == -1:
                    continue
                insertion = '\n' + content + '\n'
                html_content = html_content[:close_pos] + insertion + html_content[close_pos:]
                applied += 1
            if applied:
                handle_output(f"Insert Into Object: inserted into '{name}' ({applied} occurrence(s))" + (f" in '{scope_func}'" if scope_func else ""), "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                handle_output(f"Insert Into Object: could not find closing }} for '{name}'", "log")
                handle_output(f"Insert Into Object: could not find closing }} for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)

        elif kind == 'merge_into_object':
            # v0.7.1: Deep-merge a JSON/object literal into an existing nested object.
            # Content is expected to be one or more "key: value" lines or a JSON object
            # body (without the outer braces). Each key is checked for existence before
            # injection -- existing keys are NOT overwritten (safe idempotent merge).
            scope_func = entry.get('scope_func')
            search_space = html_content
            offset = 0
            if scope_func:
                sf_pat = _get_compiled(
                    r'(' + re.escape(scope_func) + r'\s*[=:]\s*function\s*\(.*?\)\s*\{'
                    r'|function\s+' + re.escape(scope_func) + r'\s*\(.*?\)\s*\{)',
                    re.DOTALL
                )
                sf_m = sf_pat.search(html_content)
                if sf_m:
                    sf_brace = html_content.rindex('{', sf_m.start(), sf_m.end())
                    sf_end = _bracket_match(html_content, sf_brace, '{', '}')
                    if sf_end != -1:
                        offset = sf_brace
                        search_space = html_content[sf_brace:sf_end + 1]
            pat = re.escape(name) + r'\s*[=:]\s*\{'
            matches_all = list(re.finditer(pat, search_space))
            if not matches_all:
                handle_output(f"Merge Into Object: no match for '{name}'", "log")
                handle_output(f"Merge Into Object: no match for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            applied = 0
            for m in reversed(matches_all):
                abs_start = offset + m.start()
                open_pos = html_content.find('{', abs_start)
                if open_pos == -1:
                    continue
                close_pos = _bracket_match(html_content, open_pos, '{', '}')
                if close_pos == -1:
                    continue
                obj_body = html_content[open_pos + 1:close_pos]
                # Inject only keys that do not already exist in the object body
                lines_to_inject = []
                for kv_line in content.splitlines():
                    kv_line = kv_line.strip().rstrip(',')
                    if not kv_line:
                        continue
                    key_m = re.match(r'^(["\']?[\w$]+["\']?)\s*:', kv_line)
                    if key_m:
                        key_str = key_m.group(1).strip('"\'')
                        if re.search(r'\b' + re.escape(key_str) + r'\b\s*:', obj_body):
                            handle_output(f"Merge Into Object: key '{key_str}' already exists in '{name}', skipping.", "log")
                            continue
                    lines_to_inject.append(kv_line + ',')
                if not lines_to_inject:
                    handle_output(f"Merge Into Object: all keys already present in '{name}', skipping.", "log")
                    continue
                insertion = '\n' + '\n'.join(lines_to_inject) + '\n'
                html_content = html_content[:close_pos] + insertion + html_content[close_pos:]
                applied += 1
            if applied:
                handle_output(f"Merge Into Object: merged into '{name}' ({applied} occurrence(s))", "log")
                replacements_made += 1
                successful_mods.append(mod_file)

    # v0.7.2: cache the script anchor position and script block once before the
    # mod_func_list loop. add_func previously re-found this anchor and re-sliced
    # html_content[:anchor_idx] (up to 20MB) on every directive -- 28x for your
    # mod set. Now O(1) lookup using pre-computed values from _split_html.
    _script_anchor     = '</script><tw-passagedata'
    _script_anchor_idx = html_content.find(_script_anchor)

    # v0.7.2: pre-build function name index from script_block once.
    # add_func dup check uses O(1) set lookup instead of re.search per directive.
    _func_name_pat = _get_compiled(
        r'(?:^|[\s;])([\w$.]+)\s*[=:]\s*function|function\s+([\w$.]+)\s*\(',
        re.MULTILINE
    )
    _func_name_set = set()
    for _fnm in _func_name_pat.finditer(_script_block):
        _fn = _fnm.group(1) or _fnm.group(2)
        if _fn:
            _func_name_set.add(_fn)

    # ---- Sort mod_func_list so add_func entries always precede insert_into_func ----
    # Insert Into Function targets a function that may be injected by Add Function in the
    # same mod.  Because proc_replacement_new parses IIF before Add Function, IIF entries
    # land in mod_func_list before their Add Function entries, causing "function not found"
    # at apply time.  A stable sort by kind priority fixes this without breaking cross-mod
    # ordering for other directive types.
    _KIND_ORDER = {
    'add_func':              0,
    'clone_passage':         0,  # v0.7.1: create before anything targets the new passage
    'insert_into_func':      1,
    'replace_in_func':       2,
    'replace_func':          2,
    'wrap_passage':          3,  # v0.7.1: after passage exists
    'replace_in_all_passages': 3,
    'add_storyvar':          3,
}
    mod_func_list.sort(key=lambda e: _KIND_ORDER.get(e.get('kind', ''), 0))

    # v0.7.1: [ONCE] injection tracker -- maps anchor string -> set of mod files
    # that have already injected at that anchor.  Prevents double-injection
    # when two mods share an anchor and both carry the [ONCE] modifier.
    _once_injected_anchors: set = set()

    # ---- Replace Function / Insert Before / Insert After / Delete Block ----
    # Add Function summary counters
    af_injected       = 0
    af_skipped_guard  = 0
    af_skipped_exists = 0
    af_lines_total    = 0

    # ---- v0.7.3: Batch Append To Passage + Insert After pre-pass -----------
    # Append To Passage: 205 entries across 82 mods but only ~90 unique passage
    # targets.  Previously each entry did an independent O(22MB) regex search.
    # Batch by passage name so each passage is searched exactly once.
    # Insert After: 162 entries, 145 unique anchors.  Batch by anchor so each
    # anchor is str.find'd once and all bodies are concatenated in load order.
    #
    # Guard evaluation correctness: guards are evaluated PER-ENTRY at the moment
    # each batch is applied, not all-at-once before any insertions happen.
    # This preserves the invariant that a guard sees the HTML state after all
    # prior entries have fired.  The collection pass only groups entries by key;
    # guards are not touched during collection.
    #
    # Entries processed here are marked batch_done and skipped in the main loop.

    from collections import OrderedDict as _OD

    # -- Batch Append / Prepend To Passage --
    # Collection pass: group entries by passage name in load order.
    # Guards are NOT evaluated here -- only kind + passage_name are read.
    _atp_batches = _OD()   # passage_name -> [entry dict]
    for _be in mod_func_list:
        _bk = _be.get('kind')
        if _bk not in ('append_to_passage', 'prepend_to_passage'):
            continue
        _bp = _be.get('passage_name', '')
        _atp_batches.setdefault(_bp, []).append(_be)
        _be['batch_done'] = True

    # Apply pass: for each passage, search once, then evaluate each entry's
    # guard against the current html_content (which may have grown from
    # previous passage batches) and apply bodies that pass.
    for _psg_name, _batch_entries in _atp_batches.items():
        _bpat = _get_compiled(
            r'(<tw-passagedata[^>]*name="' + re.escape(_psg_name) + r'"[^>]*>)'
            r'(.*?)(</tw-passagedata>)',
            re.DOTALL
        )
        _bpm = _bpat.search(html_content)
        if not _bpm:
            _reg_idx = (passage_names_seen.get(_psg_name) if passage_names_seen else None)
            _reg_entry = (passage_registry[_reg_idx] if _reg_idx is not None and passage_registry else None)
            if _reg_entry is not None:
                _rb = _reg_entry['body']
                for _be in _batch_entries:
                    _bg = _be.get('guards', {})
                    if not _check_guards(_bg, html_content, loaded_mod_files,
                                         passage_registry=passage_registry,
                                         passage_dict=_passage_dict,
                                         passage_meta=_passage_meta,
                                         script_block=_script_block):
                        handle_output(
                            f"Guard condition not met for 'Append To Passage [{_psg_name}]', skipping.", "log"
                        )
                        continue
                    _body = _be['body']
                    _mf   = _be['mod_file']
                    _is_pre = _be.get('kind') == 'prepend_to_passage'
                    if _body.strip() in _rb:
                        handle_output(f"Append To Passage [{_psg_name}]: already applied (registry), skipping.", "log")
                        continue
                    _rb = (_body + '\n' + _rb) if _is_pre else (_rb + '\n' + _body + '\n')
                    handle_output(f"Append To Passage (batch): registry '{_psg_name}' <- {_mf}", "log")
                    replacements_made += 1
                    successful_mods.append(_mf)
                _reg_entry['body'] = _rb
                continue
            for _be in _batch_entries:
                _bg = _be.get('guards', {})
                if not _check_guards(_bg, html_content, loaded_mod_files,
                                     passage_registry=passage_registry,
                                     passage_dict=_passage_dict,
                                     passage_meta=_passage_meta,
                                     script_block=_script_block):
                    handle_output(
                        f"Guard condition not met for 'Append To Passage [{_psg_name}]', skipping.", "log"
                    )
                    continue
                handle_output(f"Append To Passage: passage '{_psg_name}' not found", "log")
                handle_output(f"Append To Passage: passage '{_psg_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(_be['mod_file'])
            continue
        _cur_body = _bpm.group(2)
        _new_body = _cur_body
        for _be in _batch_entries:
            _bg = _be.get('guards', {})
            if not _check_guards(_bg, html_content, loaded_mod_files,
                                 passage_registry=passage_registry,
                                 passage_dict=_passage_dict,
                                 passage_meta=_passage_meta,
                                 script_block=_script_block):
                handle_output(
                    f"Guard condition not met for 'Append To Passage [{_psg_name}]', skipping.", "log"
                )
                continue
            _body   = _be['body']
            _mf     = _be['mod_file']
            _is_pre = _be.get('kind') == 'prepend_to_passage'
            # Duplicate check: body already present anywhere in accumulated result
            if _body.strip() in _new_body:
                handle_output(f"Append To Passage [{_psg_name}]: already applied, skipping.", "log")
                continue
            _new_body = (_body + '\n' + _new_body) if _is_pre else (_new_body + '\n' + _body + '\n')
            handle_output(f"Append To Passage (batch): '{_psg_name}' <- {_mf}", "log")
            replacements_made += 1
            successful_mods.append(_mf)
        if _new_body != _cur_body:
            html_content = html_content[:_bpm.start(2)] + _new_body + html_content[_bpm.end(2):]

    # -- Batch Insert After --
    # Same two-pass approach: collect by anchor (no guard eval), then apply
    # with per-entry guard evaluation against the live html_content.
    _ia_batches = _OD()   # anchor -> [entry dict]
    for _ie in mod_func_list:
        if _ie.get('kind') != 'insert_after':
            continue
        _ia_anchor = _ie['name']
        if _ie.get('once') and _ia_anchor in _once_injected_anchors:
            handle_output(f"Insert After [ONCE]: '{_ia_anchor}' already injected, skipping.", "log")
            _ie['batch_done'] = True
            continue
        _ia_batches.setdefault(_ia_anchor, []).append(_ie)
        _ie['batch_done'] = True

    for _anchor, _ia_entries in _ia_batches.items():
        _resolved_name = _resolve_pid_auto_in_anchor(_normalize_anchor(_anchor), html_content)
        _ia_idx = html_content.find(_resolved_name)
        if _ia_idx == -1 and _resolved_name != _normalize_anchor(_anchor):
            _ia_idx = html_content.find(_normalize_anchor(_anchor))
            _resolved_name = _normalize_anchor(_anchor)
        if _ia_idx == -1:
            for _ie in _ia_entries:
                _ia_guards = _ie.get('guards', {})
                if not _check_guards(_ia_guards, html_content, loaded_mod_files,
                                     passage_registry=passage_registry,
                                     passage_dict=_passage_dict,
                                     passage_meta=_passage_meta,
                                     script_block=_script_block):
                    handle_output(f"Guard condition not met for 'Insert After [{_anchor}]', skipping.", "log")
                    continue
                _fail_entry = dict(kind='insert_after', name=_anchor,
                                   body=_ie['body'], mod_file=_ie['mod_file'],
                                   once=_ie.get('once', False),
                                   soft=_ie.get('soft', False), guards={})
                _fail_msg = f"Insert After: no match for '{_anchor}'"
                if _ie.get('soft', False):
                    handle_output(f"[soft] {_fail_msg}", "log")
                else:
                    handle_output(_fail_msg, "log")
                    handle_output(_fail_msg, "failed")
                    replacements_failed += 1
                    failed_mods.append(_ie['mod_file'])
                _failed_ia_ib_entries.append(_fail_entry)
            continue
        _ia_insert = _ia_idx + len(_resolved_name)
        # v0.7.5: detect whether injection point is inside the <script> block.
        # Mirrors C# PatchEngine.IsInsideScriptBlock.  When the anchor lands in
        # raw JS, the body must stay unescaped.  When it lands in passage content,
        # the body must be escape_twine_tags encoded so <<macros>> are stored as
        # &lt;&lt;macros&gt;&gt;.  Without this check, passage-markup bodies
        # (e.g. <<set $foo to bar>>) injected into the script block produce a
        # SyntaxError because the JS parser sees 'to' as an unexpected identifier.
        _ia_in_script = _is_in_script_block(html_content, _ia_insert)
        _combined  = ''
        _combined_end = _ia_insert  # tracks end of already-combined injections
        for _ie in _ia_entries:
            _ia_guards = _ie.get('guards', {})
            if not _check_guards(_ia_guards, html_content, loaded_mod_files,
                                 passage_registry=passage_registry,
                                 passage_dict=_passage_dict,
                                 passage_meta=_passage_meta,
                                 script_block=_script_block):
                handle_output(f"Guard condition not met for 'Insert After [{_anchor}]', skipping.", "log")
                continue
            _body = _ie['body']
            _mf   = _ie['mod_file']
            # Encode body for the injection context: raw JS stays raw,
            # passage content needs <<macros>> encoded as HTML entities.
            if not _ia_in_script:
                _body = escape_twine_tags(_body)
            # Duplicate check: body present in original HTML right after anchor
            # OR already queued in _combined from a prior entry in this batch
            if (_body in html_content[_ia_insert:_ia_insert + len(_body) + 2]
                    or _body in _combined):
                handle_output(f"Insert After: already applied for '{_anchor}', skipping.", "log")
                continue
            _combined += '\n' + _body
            if _ie.get('once'):
                _once_injected_anchors.add(_anchor)
            handle_output(f"Insert After (batch): '{_anchor}' <- {_mf}", "log")
            replacements_made += 1
            successful_mods.append(_mf)
        if _combined:
            html_content = html_content[:_ia_insert] + _combined + html_content[_ia_insert:]
    # ---- end v0.7.3 batch pre-pass ----------------------------------------

    for entry in mod_func_list:
        kind     = entry['kind']
        name     = entry['name']
        mod_file = entry['mod_file']
        # v0.7.3: skip entries handled by the batch pre-pass above
        if entry.get('batch_done'):
            continue
        # v0.7.1: soft-fail -- failure goes to warnings, not FailsPatchLog
        _is_soft  = entry.get('soft', False)

        if kind == 'replace_func':
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Replace Function [{name}]', skipping.", "log")
                continue
            # Find the function by name and replace its entire body.
            # Supports: name = function(...) { }, function name(...) { }, name(...) { } (method)
            pat = _get_compiled(
                r'(' + re.escape(name) + r'\s*[=:]\s*function\s*\(.*?\)\s*\{' +
                r'|function\s+' + re.escape(name) + r'\s*\(.*?\)\s*\{)',
                re.DOTALL
            )
            m = pat.search(html_content)
            if not m:
                handle_output(f"Replace Function: no match for '{name}'", "log")
                handle_output(f"Replace Function: no match for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            # Find the opening brace of the function body
            brace_open = html_content.rindex('{', m.start(), m.end())
            brace_close = _bracket_match(html_content, brace_open, '{', '}')
            if brace_close == -1:
                handle_output(f"Replace Function: could not match body for '{name}'", "log")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            new_body = entry['body']
            if new_body in html_content[m.start():brace_close + 1]:
                handle_output(f"Replace Function: already applied for '{name}', skipping.", "log")
                continue
            html_content = html_content[:brace_open + 1] + '\n' + new_body + '\n' + html_content[brace_close:]
            handle_output(f"Replace Function: replaced body of '{name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'insert_before':
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Insert Before [{name}]', skipping.", "log")
                continue
            # v0.7.1: [ONCE] -- skip if any mod already injected at this anchor
            if entry.get('once') and name in _once_injected_anchors:
                handle_output(f"Insert Before [ONCE]: anchor '{name}' already injected, skipping.", "log")
                continue
            resolved_name = _resolve_pid_auto_in_anchor(_normalize_anchor(name), html_content)
            idx = html_content.find(resolved_name)
            if idx == -1 and resolved_name != _normalize_anchor(name):
                idx = html_content.find(_normalize_anchor(name))  # fallback to original
            if idx == -1:
                _fail_msg = f"Insert Before: no match for '{name}'"
                if _is_soft:
                    handle_output(f"[soft] {_fail_msg}", "log")
                else:
                    handle_output(_fail_msg, "log")
                    handle_output(_fail_msg, "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                _failed_ia_ib_entries.append(entry)
                continue
            body = entry['body']
            # v0.7.5: encode body for context. Passage content needs <<macros>>
            # escaped; script block content must stay raw.
            if not _is_in_script_block(html_content, idx):
                body = escape_twine_tags(body)
            if body in html_content[max(0, idx - len(body) - 2):idx + 2]:
                handle_output(f"Insert Before: already applied for '{name}', skipping.", "log")
                continue
            html_content = html_content[:idx] + body + '\n' + html_content[idx:]
            if entry.get('once'):
                _once_injected_anchors.add(name)
            handle_output(f"Insert Before: inserted before '{name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'insert_after':
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Insert After [{name}]', skipping.", "log")
                continue
            # v0.7.1: [ONCE] -- skip if any mod already injected at this anchor
            if entry.get('once') and name in _once_injected_anchors:
                handle_output(f"Insert After [ONCE]: anchor '{name}' already injected, skipping.", "log")
                continue
            resolved_name = _resolve_pid_auto_in_anchor(_normalize_anchor(name), html_content)
            idx = html_content.find(resolved_name)
            if idx == -1 and resolved_name != _normalize_anchor(name):
                idx = html_content.find(_normalize_anchor(name))  # fallback to original
            if idx == -1:
                _fail_msg = f"Insert After: no match for '{name}'"
                if _is_soft:
                    handle_output(f"[soft] {_fail_msg}", "log")
                else:
                    handle_output(_fail_msg, "log")
                    handle_output(_fail_msg, "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                _failed_ia_ib_entries.append(entry)
                continue
            insert_pos = idx + len(resolved_name)
            body = entry['body']
            # v0.7.5: encode body for context. Passage content needs <<macros>>
            # escaped; script block content must stay raw.
            if not _is_in_script_block(html_content, insert_pos):
                body = escape_twine_tags(body)
            if body in html_content[insert_pos:insert_pos + len(body) + 2]:
                handle_output(f"Insert After: already applied for '{name}', skipping.", "log")
                continue
            html_content = html_content[:insert_pos] + '\n' + body + html_content[insert_pos:]
            if entry.get('once'):
                _once_injected_anchors.add(name)
            handle_output(f"Insert After: inserted after '{name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'delete_block':
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Delete Block [{name}]', skipping.", "log")
                continue
            # v0.7.0: use KittyHTMLLayer DOM op; fall back to regex if BS4 unavailable
            if _html_layer.bs4_available:
                if not _html_layer.passage_exists(name):
                    handle_output(f"Delete Block: no passage named '{name}' found", "log")
                    handle_output(f"Delete Block: no passage named '{name}' found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                _html_layer.delete_passage(name)
                _html_layer.sync_raw()
                html_content = _html_layer._raw
            else:
                pat = _get_compiled(
                    r'<tw-passagedata[^>]*name="' + re.escape(name) + r'"[^>]*>.*?</tw-passagedata>',
                    re.DOTALL
                )
                m = pat.search(html_content)
                if not m:
                    handle_output(f"Delete Block: no passage named '{name}' found", "log")
                    handle_output(f"Delete Block: no passage named '{name}' found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                html_content = html_content[:m.start()] + html_content[m.end():]
            # Remove from original-names snapshot so a subsequent Add Passage
            # for the same name is not incorrectly skipped.
            _original_passage_names.discard(name)
            handle_output(f"Delete Block: deleted passage '{name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

            # v0.6.0 fix: early-inject replacement passage from registry.
            # If the passage_registry contains an Add Passage for the same name,
            # inject it now so that subsequent Phase 4 directives (Replace In
            # Passage, Append/Prepend To Passage, Insert After targeting anchors
            # inside the passage, etc.) can operate on the replacement.
            if passage_registry and passage_names_seen and name in passage_names_seen:
                _reg_idx = passage_names_seen[name]
                _reg_entry = passage_registry[_reg_idx]
                _reg_guards = _reg_entry.get('guards', {})
                if _check_guards(_reg_guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                    _reg_body = _reg_entry['body']
                    _reg_tags = _reg_entry.get('tags', '')
                    _reg_body = escape_html_between_tags(_reg_body)
                    _reg_body = escape_twine_tags(_reg_body)
                    _reg_body = auto_escape_passage_bodies(_reg_body)
                    _reg_tag = (
                        f'<tw-passagedata pid="auto" name="{name}" tags="{_reg_tags}" '
                        f'position="100,100" size="100,100">'
                        f'{_reg_body}'
                        f'</tw-passagedata>'
                    )
                    _psg_warnings = check_injection_tag_balance(
                        _reg_tag, 0, f"Delete Block + Add Passage [{name}] from {_reg_entry['mod_file']}"
                    )
                    for _pw in _psg_warnings:
                        handle_output(_pw, 'alllogs')
                    storydata_close = html_content.find('</tw-storydata>')
                    if storydata_close != -1:
                        html_content = html_content[:storydata_close] + '\n' + _reg_tag + '\n' + html_content[storydata_close:]
                    _reg_entry['early_injected'] = True
                    handle_output(
                        f"Delete Block: early-injected replacement '{name}' from {_reg_entry['mod_file']}",
                        "log"
                    )
                else:
                    handle_output(
                        f"Delete Block: replacement '{name}' in registry but guard not met, deferring to Phase 7",
                        "log"
                    )

        elif kind == 'replace_in_passage':
            passage_name = entry['passage_name']
            anchor       = _normalize_anchor(entry['name'])
            new_body     = entry['body']
            guards       = entry['guards']

            # Evaluate guard clauses
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Replace In Passage [{passage_name}]', skipping.", "log")
                continue

            # Locate the named passage
            # v0.7.2 fix: passage-dict fast path removed for all passage-write handlers.
            # _DictPassageMatch used stale absolute positions (built before Phase 4 writes).
            # Each Append/Prepend/RIP/Delete grows or shrinks html_content, shifting
            # all subsequent passage abs_start values. Using the stale dict caused writes
            # to wrong positions -- including into the JS block -- producing corrupt HTML.
            # Live regex search is O(N) per operation but always correct.
            passage_pat = _get_compiled(
                r'(<tw-passagedata[^>]*name="' + re.escape(passage_name) + r'"[^>]*>)'
                r'(.*?)'
                r'(</tw-passagedata>)',
                re.DOTALL
            )
            pm = passage_pat.search(html_content)

            if pm:
                passage_body = pm.group(2)
                anchor_pat = re.escape(anchor).replace(r'\n', r'\s*\n\s*')
                if not _fast_search(anchor_pat, passage_body):
                    handle_output(
                        f"Replace In Passage [{passage_name}]: anchor not found in passage body -- "
                        f"falling back to full-HTML Replace:", "log"
                    )
                    # Graceful fallback: try full-HTML search
                    if anchor not in html_content:
                        handle_output(f"Replace In Passage [{passage_name}]: no match in full HTML either", "failed")
                        replacements_failed += 1
                        failed_mods.append(mod_file)
                        continue
                    # Duplicate check for full-HTML fallback
                    idx_fb = html_content.find(anchor)
                    if new_body in html_content[idx_fb:idx_fb + len(anchor) + len(new_body) + 10]:
                        handle_output(f"Replace In Passage [{passage_name}]: already applied (full HTML), skipping.", "log")
                        continue
                    html_content = html_content.replace(anchor, new_body, 1)
                    handle_output(f"Replace In Passage [{passage_name}]: applied via full-HTML fallback", "log")
                    replacements_made += 1
                    successful_mods.append(mod_file)
                    continue

                # Duplicate-patch check within passage scope
                if re.search(re.escape(new_body), passage_body):
                    handle_output(f"Replace In Passage [{passage_name}]: already applied, skipping.", "log")
                    continue

                new_passage_body = re.sub(anchor_pat, lambda _m: new_body, passage_body, count=1)
                html_content = (
                    html_content[:pm.start(2)]
                    + new_passage_body
                    + html_content[pm.end(2):]
                )
                handle_output(f"Replace In Passage [{passage_name}]: replaced '{anchor[:60]}'", "log")
                replacements_made += 1
                successful_mods.append(mod_file)

            else:
                # Passage not found in live HTML -- check passage registry
                # (passages queued for Phase 7 injection by Add Passage).
                # Registry bodies may be RAW (shorthand format: <<macros>>) or
                # pre-escaped (full format: &lt;&lt;macros&gt;&gt;).  The RIP anchor
                # is always written in escaped form.  We try the encoded anchor
                # first (matches full-format registry bodies), then unescape
                # both anchor and replacement to match shorthand registry bodies.
                _rip_registry_hit = False
                if passage_registry and passage_names_seen and passage_name in passage_names_seen:
                    _rip_reg_idx = passage_names_seen[passage_name]
                    _rip_reg_entry = passage_registry[_rip_reg_idx]
                    _rip_reg_body = _rip_reg_entry.get('body', '')

                    # Determine which form matches: encoded or raw
                    _rip_raw_anchor = html.unescape(anchor)
                    _rip_raw_new    = html.unescape(new_body)

                    _rip_use_anchor = None
                    _rip_use_new    = None
                    _rip_match_kind = None

                    if anchor in _rip_reg_body:
                        # Encoded anchor matches (full-format body already escaped)
                        _rip_use_anchor = anchor
                        _rip_use_new    = new_body
                        _rip_match_kind = "encoded"
                    elif _rip_raw_anchor in _rip_reg_body:
                        # Raw/unescaped anchor matches (shorthand body)
                        _rip_use_anchor = _rip_raw_anchor
                        _rip_use_new    = _rip_raw_new
                        _rip_match_kind = "unescaped"

                    if _rip_use_anchor is not None:
                        _rip_reg_entry['body'] = _rip_reg_body.replace(_rip_use_anchor, _rip_use_new, 1)
                        handle_output(
                            f"Replace In Passage [{passage_name}]: passage found in registry "
                            f"(Phase 7 pending) -- applied replacement to registry body ({_rip_match_kind})", "log"
                        )
                        replacements_made += 1
                        successful_mods.append(mod_file)
                        _rip_registry_hit = True
                    else:
                        # Neither form matched exactly -- try flexible whitespace
                        for _rip_try_anchor, _rip_try_new, _rip_try_label in [
                            (anchor, new_body, "encoded flex"),
                            (_rip_raw_anchor, _rip_raw_new, "unescaped flex"),
                        ]:
                            _rip_anchor_pat = re.escape(_rip_try_anchor).replace(r'\n', r'\s*\n\s*')
                            _rip_flex_m = _fast_search(_rip_anchor_pat, _rip_reg_body)
                            if _rip_flex_m:
                                _rip_reg_entry['body'] = (
                                    _rip_reg_body[:_rip_flex_m.start()]
                                    + _rip_try_new
                                    + _rip_reg_body[_rip_flex_m.end():]
                                )
                                handle_output(
                                    f"Replace In Passage [{passage_name}]: passage found in registry "
                                    f"(Phase 7 pending) -- applied replacement to registry body ({_rip_try_label})", "log"
                                )
                                replacements_made += 1
                                successful_mods.append(mod_file)
                                _rip_registry_hit = True
                                break

                if _rip_registry_hit:
                    continue

                # Passage not in registry either -- fall back to full-HTML Replace:
                handle_output(
                    f"Replace In Passage [{passage_name}]: passage not found -- "
                    f"falling back to full-HTML Replace:", "log"
                )
                if anchor not in html_content:
                    handle_output(f"Replace In Passage [{passage_name}]: no match in full HTML either", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                idx_fb = html_content.find(anchor)
                if new_body in html_content[idx_fb:idx_fb + len(anchor) + len(new_body) + 10]:
                    handle_output(f"Replace In Passage [{passage_name}]: already applied (full HTML fallback), skipping.", "log")
                    continue
                html_content = html_content.replace(anchor, new_body, 1)
                handle_output(f"Replace In Passage [{passage_name}]: applied via full-HTML fallback", "log")
                replacements_made += 1
                successful_mods.append(mod_file)

        elif kind == 'delete_span':
            start_anchor = _normalize_anchor(entry['name'])
            end_anchor   = _normalize_anchor(entry['end_anchor'])
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Delete Span [{start_anchor[:40]}]', skipping.", "log")
                continue

            start_idx = html_content.find(start_anchor)
            if start_idx == -1:
                handle_output(f"Delete Span: start anchor not found: '{start_anchor[:60]}'", "log")
                handle_output(f"Delete Span: start anchor not found: '{start_anchor[:60]}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue

            end_search_start = start_idx + len(start_anchor)
            end_idx = html_content.find(end_anchor, end_search_start)
            if end_idx == -1:
                handle_output(f"Delete Span: end anchor not found after start: '{end_anchor[:60]}'", "log")
                handle_output(f"Delete Span: end anchor not found after start: '{end_anchor[:60]}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue

            span_end = end_idx + len(end_anchor)

            # Duplicate check: if start_anchor is immediately followed by content
            # after the span (i.e. the span was already deleted), skip.
            content_after_span = html_content[span_end:span_end + 20]
            content_after_start = html_content[start_idx + len(start_anchor):start_idx + len(start_anchor) + 20]
            if content_after_start == content_after_span:
                handle_output(f"Delete Span: already applied, skipping.", "log")
                continue

            deleted = html_content[start_idx:span_end]
            html_content = html_content[:start_idx] + html_content[span_end:]
            handle_output(
                f"Delete Span: deleted {len(deleted)} chars "
                f"from '{start_anchor[:40]}' to '{end_anchor[:40]}'", "log"
            )
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'prepend_to_passage':
            passage_name = entry['passage_name']
            body         = entry['body']
            guards       = entry['guards']

            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Prepend To Passage [{passage_name}]', skipping.", "log")
                continue

            # v0.7.2 fix: passage-dict fast path removed for all passage-write handlers.
            # _DictPassageMatch used stale absolute positions (built before Phase 4 writes).
            # Each Append/Prepend/RIP/Delete grows or shrinks html_content, shifting
            # all subsequent passage abs_start values. Using the stale dict caused writes
            # to wrong positions -- including into the JS block -- producing corrupt HTML.
            # Live regex search is O(N) per operation but always correct.
            passage_pat = _get_compiled(
                r'(<tw-passagedata[^>]*name="' + re.escape(passage_name) + r'"[^>]*>)'
                r'(.*?)'
                r'(</tw-passagedata>)',
                re.DOTALL
            )
            pm = passage_pat.search(html_content)
            if not pm:
                # Fallback: passage may be pending in passage_registry (added by an earlier mod).
                # v0.7.2: O(1) registry lookup via passage_names_seen dict
                # instead of O(R) linear scan through passage_registry list.
                _reg_idx = (passage_names_seen.get(passage_name) if passage_names_seen else None)
                reg_entry = (passage_registry[_reg_idx] if _reg_idx is not None and passage_registry else None)
                if reg_entry is not None:
                    reg_body = reg_entry['body']
                    if not reg_body.lstrip('\n').startswith(body.strip()):
                        reg_entry['body'] = '\n' + body + '\n' + reg_body
                        handle_output(f"Prepend To Passage: prepended to registry entry '{passage_name}'", "log")
                        replacements_made += 1
                        successful_mods.append(mod_file)
                    else:
                        handle_output(f"Prepend To Passage [{passage_name}]: already applied (registry), skipping.", "log")
                    continue
                handle_output(f"Prepend To Passage: passage '{passage_name}' not found", "log")
                handle_output(f"Prepend To Passage: passage '{passage_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue

            # Duplicate check: body already present at the very start of the passage
            passage_body = pm.group(2)
            if passage_body.lstrip('\n').startswith(body.strip()):
                handle_output(f"Prepend To Passage [{passage_name}]: already applied, skipping.", "log")
                continue

            new_body = '\n' + body + '\n' + passage_body
            html_content = html_content[:pm.start(2)] + new_body + html_content[pm.end(2):]
            handle_output(f"Prepend To Passage: prepended to '{passage_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)


        elif kind == 'append_to_passage':
            passage_name = entry['passage_name']
            body         = entry['body']
            guards       = entry['guards']

            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Append To Passage [{passage_name}]', skipping.", "log")
                continue

            # v0.7.2 fix: passage-dict fast path removed for all passage-write handlers.
            # _DictPassageMatch used stale absolute positions (built before Phase 4 writes).
            # Each Append/Prepend/RIP/Delete grows or shrinks html_content, shifting
            # all subsequent passage abs_start values. Using the stale dict caused writes
            # to wrong positions -- including into the JS block -- producing corrupt HTML.
            # Live regex search is O(N) per operation but always correct.
            passage_pat = _get_compiled(
                r'(<tw-passagedata[^>]*name="' + re.escape(passage_name) + r'"[^>]*>)'
                r'(.*?)'
                r'(</tw-passagedata>)',
                re.DOTALL
            )
            pm = passage_pat.search(html_content)
            if not pm:
                # Fallback: passage may be pending in passage_registry (added by an earlier mod).
                # v0.7.2: O(1) registry lookup via passage_names_seen dict
                # instead of O(R) linear scan through passage_registry list.
                _reg_idx = (passage_names_seen.get(passage_name) if passage_names_seen else None)
                reg_entry = (passage_registry[_reg_idx] if _reg_idx is not None and passage_registry else None)
                if reg_entry is not None:
                    reg_body = reg_entry['body']
                    if not reg_body.rstrip('\n').endswith(body.strip()):
                        reg_entry['body'] = reg_body + '\n' + body + '\n'
                        handle_output(f"Append To Passage: appended to registry entry '{passage_name}'", "log")
                        replacements_made += 1
                        successful_mods.append(mod_file)
                    else:
                        handle_output(f"Append To Passage [{passage_name}]: already applied (registry), skipping.", "log")
                    continue
                handle_output(f"Append To Passage: passage '{passage_name}' not found", "log")
                handle_output(f"Append To Passage: passage '{passage_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue

            # Duplicate check: body already present at the very end of the passage
            passage_body = pm.group(2)
            if passage_body.rstrip('\n').endswith(body.strip()):
                handle_output(f"Append To Passage [{passage_name}]: already applied, skipping.", "log")
                continue

            new_body = passage_body + '\n' + body + '\n'
            html_content = html_content[:pm.start(2)] + new_body + html_content[pm.end(2):]
            handle_output(f"Append To Passage: appended to '{passage_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)


        elif kind == 'add_tag_to_passage':
            passage_name = entry['passage_name']
            new_tags     = entry['tags'].split()
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Add Tag To Passage [{passage_name}]', skipping.", "log")
                continue

            if _html_layer.bs4_available:
                if not _html_layer.passage_exists(passage_name):
                    handle_output(f"Add Tag To Passage: passage '{passage_name}' not found", "log")
                    handle_output(f"Add Tag To Passage: passage '{passage_name}' not found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                current_tags = (_html_layer.get_passage_tags_attr(passage_name) or "").split()
                tags_to_add = [t for t in new_tags if t not in current_tags]
                if not tags_to_add:
                    handle_output(f"Add Tag To Passage [{passage_name}]: all tags already present, skipping.", "log")
                    continue
                for t in tags_to_add:
                    _html_layer.add_passage_tag(passage_name, t)
                _html_layer.sync_raw()
                html_content = _html_layer._raw
            else:
                tag_pat = _get_compiled(
                    r'(<tw-passagedata[^>]*name="' + re.escape(passage_name) + r'"[^>]*)'
                    r'(tags="([^"]*)")'
                    r'([^>]*>)',
                    re.DOTALL
                )
                tm = tag_pat.search(html_content)
                if not tm:
                    handle_output(f"Add Tag To Passage: passage '{passage_name}' not found", "log")
                    handle_output(f"Add Tag To Passage: passage '{passage_name}' not found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                current_tags = tm.group(3).split()
                tags_to_add = [t for t in new_tags if t not in current_tags]
                if not tags_to_add:
                    handle_output(f"Add Tag To Passage [{passage_name}]: all tags already present, skipping.", "log")
                    continue
                new_tag_attr = 'tags="' + ' '.join(current_tags + tags_to_add) + '"'
                html_content = html_content[:tm.start(2)] + new_tag_attr + html_content[tm.end(2):]
            handle_output(f"Add Tag To Passage: added {tags_to_add} to '{passage_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'remove_tag_from_passage':
            passage_name = entry['passage_name']
            tags_to_remove = set(entry['tags'].split())
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Remove Tag From Passage [{passage_name}]', skipping.", "log")
                continue

            if _html_layer.bs4_available:
                if not _html_layer.passage_exists(passage_name):
                    handle_output(f"Remove Tag From Passage: passage '{passage_name}' not found", "log")
                    handle_output(f"Remove Tag From Passage: passage '{passage_name}' not found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                current_tags = (_html_layer.get_passage_tags_attr(passage_name) or "").split()
                remaining = [t for t in current_tags if t not in tags_to_remove]
                if remaining == current_tags:
                    handle_output(f"Remove Tag From Passage [{passage_name}]: no matching tags found, skipping.", "log")
                    continue
                removed = tags_to_remove - set(remaining)
                for t in removed:
                    _html_layer.remove_passage_tag(passage_name, t)
                _html_layer.sync_raw()
                html_content = _html_layer._raw
            else:
                tag_pat = _get_compiled(
                    r'(<tw-passagedata[^>]*name="' + re.escape(passage_name) + r'"[^>]*)'
                    r'(tags="([^"]*)")'
                    r'([^>]*>)',
                    re.DOTALL
                )
                tm = tag_pat.search(html_content)
                if not tm:
                    handle_output(f"Remove Tag From Passage: passage '{passage_name}' not found", "log")
                    handle_output(f"Remove Tag From Passage: passage '{passage_name}' not found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                current_tags = tm.group(3).split()
                remaining = [t for t in current_tags if t not in tags_to_remove]
                if remaining == current_tags:
                    handle_output(f"Remove Tag From Passage [{passage_name}]: no matching tags found, skipping.", "log")
                    continue
                removed = tags_to_remove - set(remaining)
                new_tag_attr = 'tags="' + ' '.join(remaining) + '"'
                html_content = html_content[:tm.start(2)] + new_tag_attr + html_content[tm.end(2):]
            handle_output(f"Remove Tag From Passage: removed {sorted(removed)} from '{passage_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'add_func':
            name = entry['name']
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Add Function [{name}]', skipping.", "log")
                af_skipped_guard += 1
                continue
            # Inject a new function into the script block.
            # Target anchor: </script><tw-passagedata (same as Add Javascript:)
            # v0.7.2: use cached anchor position and _script_block from _split_html.
            # Avoids re-finding the anchor and re-slicing 20MB per Add Function directive.
            anchor_idx = _script_anchor_idx
            if anchor_idx == -1:
                handle_output(f"Add Function: script anchor not found for '{name}'", "log")
                handle_output(f"Add Function: script anchor not found for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            # Duplicate check: if the function name already exists in the script block
            # (either vanilla or from a previous patch run), skip it.
            # Use _script_block from _split_html (0.1MB) instead of html_content[:anchor_idx] (20MB).
            script_block = _script_block
            func_pat = _get_compiled(
                r'(?:^|[\s;])' + re.escape(name) + r'\s*[=:]\s*function'
                r'|function\s+' + re.escape(name) + r'\s*\(',
                re.MULTILINE
            )
            # v0.7.2: O(1) index lookup
            if name in _func_name_set:
                handle_output(f"Add Function: '{name}' already exists, skipping.", "log")
                af_skipped_exists += 1
                continue
            body = entry['body']
            line_count = body.count('\n') + 1
            # Re-find anchor at inject time -- html_content grows with each injection
            # so the cached position drifts. O(n) but only on successful injections.
            _live_anchor_idx = html_content.find(_script_anchor)
            if _live_anchor_idx == -1:
                handle_output(f"Add Function: script anchor lost after prior injection for '{name}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            injection = '\n\n' + body + '\n'
            html_content = html_content[:_live_anchor_idx] + injection + html_content[_live_anchor_idx:]
            # Keep _script_block in sync for subsequent dup checks in this loop
            _script_block = html_content[:html_content.find(_script_anchor)]
            _func_name_set.add(name)  # keep index in sync
            handle_output(f"Add Function: injected '{name}' ({line_count} lines)", "log")
            af_injected += 1
            af_lines_total += line_count
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'rename_passage':
            new_name = entry['new_name']
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Rename Passage [{name}]', skipping.", "log")
                continue
            if _html_layer.bs4_available:
                if not _html_layer.passage_exists(name):
                    handle_output(f"Rename Passage: no passage named '{name}' found", "log")
                    handle_output(f"Rename Passage: no passage named '{name}' found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                _html_layer.rename_passage(name, new_name)
                _html_layer.sync_raw()
                html_content = _html_layer._raw
            else:
                pat = _get_compiled(
                    r'(<tw-passagedata[^>]*name=")' + re.escape(name) + r'(")',
                )
                m = pat.search(html_content)
                if not m:
                    handle_output(f"Rename Passage: no passage named '{name}' found", "log")
                    handle_output(f"Rename Passage: no passage named '{name}' found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                html_content = html_content[:m.start(1)] + m.group(1) + new_name + m.group(2) + html_content[m.end():]
            handle_output(f"Rename Passage: renamed '{name}' -> '{new_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'add_variable':
            varname = entry['name']
            value   = entry.get('value', 'undefined')
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Add Variable [{varname}]', skipping.", "log")
                continue
            # Inject into StoryInit passage
            si_pat = _get_compiled(
                r'<tw-passagedata[^>]*name="StoryInit"[^>]*>(.*?)</tw-passagedata>',
                re.DOTALL
            )
            si_m = si_pat.search(html_content)
            if not si_m:
                handle_output(f"Add Variable: StoryInit passage not found for '{varname}'", "log")
                handle_output(f"Add Variable: StoryInit passage not found for '{varname}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            # Duplicate check: skip if variable name already appears in StoryInit
            init_body = si_m.group(1)
            var_pat = _get_compiled(r'\$' + re.escape(varname) + r'\b')
            if var_pat.search(init_body):
                handle_output(f"Add Variable: '{varname}' already in StoryInit, skipping.", "log")
                continue
            set_line = f'&lt;&lt;set ${varname} to {value}&gt;&gt;'
            insert_pos = si_m.start(1)
            html_content = html_content[:insert_pos] + set_line + '\n' + html_content[insert_pos:]
            handle_output(f"Add Variable: injected '${varname}' into StoryInit", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'insert_into_func':
            func_name  = entry['name']
            anchor_raw = entry['anchor']
            body_raw   = entry['body']
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Insert Into Function [{func_name}]', skipping.", "log")
                continue
            # Find the function body
            fp = _get_compiled(
                r'(' + re.escape(func_name) + r'\s*[=:]\s*function\s*\(.*?\)\s*\{'
                r'|function\s+' + re.escape(func_name) + r'\s*\(.*?\)\s*\{)',
                re.DOTALL
            )
            fm = fp.search(html_content)
            if not fm:
                handle_output(f"Insert Into Function: function '{func_name}' not found", "log")
                handle_output(f"Insert Into Function: function '{func_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            fb_open = html_content.rindex('{', fm.start(), fm.end())
            fb_close = _bracket_match(html_content, fb_open, '{', '}')
            if fb_close == -1:
                handle_output(f"Insert Into Function: could not find body end for '{func_name}'", "log")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            func_body = html_content[fb_open:fb_close + 1]
            anchor_idx = func_body.find(anchor_raw)
            if anchor_idx == -1:
                handle_output(f"Insert Into Function: anchor not found in '{func_name}': '{anchor_raw[:60]}'", "log")
                handle_output(f"Insert Into Function: anchor not found in '{func_name}': '{anchor_raw[:60]}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            if body_raw in func_body:
                handle_output(f"Insert Into Function: already applied in '{func_name}', skipping.", "log")
                continue
            insert_abs = fb_open + anchor_idx + len(anchor_raw)
            html_content = html_content[:insert_abs] + '\n' + body_raw + html_content[insert_abs:]
            handle_output(f"Insert Into Function: injected into '{func_name}' after '{anchor_raw[:40]}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'replace_func_sig':
            func_name  = entry['name']
            new_params = entry['new_params']
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Replace Function Signature [{func_name}]', skipping.", "log")
                continue
            fp = _get_compiled(
                r'(' + re.escape(func_name) + r'\s*[=:]\s*function\s*\()([^)]*)(\))'
                r'|(?P<kw>function\s+' + re.escape(func_name) + r'\s*\()([^)]*)(?P<cp>\))',
                re.DOTALL
            )
            fm = fp.search(html_content)
            if not fm:
                handle_output(f"Replace Function Signature: '{func_name}' not found", "log")
                handle_output(f"Replace Function Signature: '{func_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            # Determine which match group holds the param content
            if fm.group(2) is not None:
                # Assignment style: name = function(PARAMS)
                p_start = fm.start(2)
                p_end   = fm.end(2)
            else:
                # Declaration style: function name(PARAMS)
                p_start = fm.start(5)
                p_end   = fm.end(5)
            current_params = html_content[p_start:p_end]
            if current_params.strip() == new_params.strip():
                handle_output(f"Replace Function Signature: already applied for '{func_name}', skipping.", "log")
                continue
            html_content = html_content[:p_start] + new_params + html_content[p_end:]
            handle_output(f"Replace Function Signature: updated params of '{func_name}' -> ({new_params})", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'replace_in_func':
            func_name  = entry['name']
            anchor_raw = entry['anchor']
            body_raw   = entry['body']
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Replace In Function [{func_name}]', skipping.", "log")
                continue
            fp = _get_compiled(
                r'(' + re.escape(func_name) + r'\s*[=:]\s*function\s*\(.*?\)\s*\{'
                r'|function\s+' + re.escape(func_name) + r'\s*\(.*?\)\s*\{)',
                re.DOTALL
            )
            fm = fp.search(html_content)
            if not fm:
                handle_output(f"Replace In Function: function '{func_name}' not found", "log")
                handle_output(f"Replace In Function: function '{func_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            fb_open = html_content.rindex('{', fm.start(), fm.end())
            fb_close = _bracket_match(html_content, fb_open, '{', '}')
            if fb_close == -1:
                handle_output(f"Replace In Function: could not find body end for '{func_name}'", "log")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            func_body = html_content[fb_open:fb_close + 1]
            anchor_idx = func_body.find(anchor_raw)
            if anchor_idx == -1:
                handle_output(f"Replace In Function: anchor not found in '{func_name}': '{anchor_raw[:60]}'", "log")
                handle_output(f"Replace In Function: anchor not found in '{func_name}': '{anchor_raw[:60]}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            if body_raw in func_body:
                handle_output(f"Replace In Function: already applied in '{func_name}', skipping.", "log")
                continue
            # Replace the anchor with the body within the function scope
            replace_abs_start = fb_open + anchor_idx
            replace_abs_end = replace_abs_start + len(anchor_raw)
            html_content = html_content[:replace_abs_start] + body_raw + html_content[replace_abs_end:]
            handle_output(f"Replace In Function: replaced '{anchor_raw[:40]}' in '{func_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'delete_in_passage':
            passage_name = entry['passage_name']
            anchor       = entry['name']
            guards       = entry['guards']

            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Delete In Passage [{passage_name}]', skipping.", "log")
                continue

            # v0.7.2 fix: passage-dict fast path removed for all passage-write handlers.
            # _DictPassageMatch used stale absolute positions (built before Phase 4 writes).
            # Each Append/Prepend/RIP/Delete grows or shrinks html_content, shifting
            # all subsequent passage abs_start values. Using the stale dict caused writes
            # to wrong positions -- including into the JS block -- producing corrupt HTML.
            # Live regex search is O(N) per operation but always correct.
            passage_pat = _get_compiled(
                r'(<tw-passagedata[^>]*name="' + re.escape(passage_name) + r'"[^>]*>)'
                r'(.*?)'
                r'(</tw-passagedata>)',
                re.DOTALL
            )
            pm = passage_pat.search(html_content)

            if pm:
                passage_body = pm.group(2)
                anchor_pat = re.escape(anchor).replace(r'\n', r'\s*\n\s*')
                if not _fast_search(anchor_pat, passage_body):
                    handle_output(
                        f"Delete In Passage [{passage_name}]: anchor not found in passage body",
                        "log"
                    )
                    handle_output(
                        f"Delete In Passage [{passage_name}]: anchor not found in passage body",
                        "failed"
                    )
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
                # Check already deleted
                new_passage_body = re.sub(anchor_pat, '', passage_body, count=1)
                if new_passage_body == passage_body:
                    handle_output(f"Delete In Passage [{passage_name}]: already applied, skipping.", "log")
                    continue
                html_content = (
                    html_content[:pm.start(2)]
                    + new_passage_body
                    + html_content[pm.end(2):]
                )
                handle_output(f"Delete In Passage [{passage_name}]: deleted '{anchor[:60]}'", "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                handle_output(f"Delete In Passage [{passage_name}]: passage not found", "log")
                handle_output(f"Delete In Passage [{passage_name}]: passage not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)

        elif kind == 'move_passage':
            old_pname = entry['name']
            new_pname = entry['new_name']
            guards = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Move Passage [{old_pname}]', skipping.", "log")
                continue

            # Step 1: Rename the passage tag
            rename_pat = _get_compiled(
                r'(<tw-passagedata[^>]*name=")' + re.escape(old_pname) + r'(")',
            )
            rm = rename_pat.search(html_content)
            if not rm:
                handle_output(f"Move Passage: no passage named '{old_pname}' found", "log")
                handle_output(f"Move Passage: no passage named '{old_pname}' found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue

            html_content = html_content[:rm.start(1)] + rm.group(1) + new_pname + rm.group(2) + html_content[rm.end():]

            # Step 2: Update all references throughout the HTML
            # v0.7.2: scope reference updates to passage bodies + script_block
            # instead of running re.subn on the full 20MB html_content.
            ref_count = 0
            old_escaped = html.escape(old_pname)
            new_escaped = html.escape(new_pname)

            _ref_patterns = [
                (r'(&lt;&lt;(?:goto|link|display|include)\s+["\']?)' + re.escape(old_escaped) + r'(["\']?\s*&gt;&gt;)',
                 r'\1' + new_escaped + r'\2'),
                (r'(passage:\s*["\'])' + re.escape(old_pname) + r'(["\'])',
                 r'\1' + new_pname + r'\2'),
                (r'(&lt;&lt;link\s+[^&]*?["\'].*?["\'],\s*["\']?)' + re.escape(old_escaped) + r'(["\']?\s*&gt;&gt;)',
                 r'\1' + new_escaped + r'\2'),
            ]
            # Apply to each passage body individually via _passage_dict
            for _ref_pname, _ref_body in list(_passage_dict.items()):
                _new_ref_body = _ref_body
                for _rp, _rr in _ref_patterns:
                    _new_ref_body, _n = re.subn(_rp, _rr, _new_ref_body)
                    ref_count += _n
                if _new_ref_body != _ref_body:
                    _passage_dict[_ref_pname] = _new_ref_body
                    # Write back to html_content immediately for this passage
                    _ref_meta = _passage_meta[_ref_pname]
                    _ref_open, _ref_abs_start, _ref_abs_end = _ref_meta
                    _ref_body_start = _ref_abs_start + len(_ref_open)
                    _ref_body_end   = _ref_abs_end - len('</tw-passagedata>')
                    html_content = html_content[:_ref_body_start] + _new_ref_body + html_content[_ref_body_end:]
            # Also update script block (passage: references in event registrations)
            for _rp, _rr in _ref_patterns:
                _new_script, _n = re.subn(_rp, _rr, _script_block)
                if _n:
                    html_content = html_content.replace(_script_block, _new_script, 1)
                    _script_block = _new_script
                    ref_count += _n

            handle_output(
                f"Move Passage: renamed '{old_pname}' -> '{new_pname}' "
                f"and updated {ref_count} reference(s)",
                "log"
            )
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'clone_passage':
            # v0.7.1: Copy an existing passage and register it under a new name.
            # Source may be in live HTML or in passage_registry (Add Passage queued).
            src_name = name
            dst_name = entry['new_name']
            guards   = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Clone Passage [{src_name}]', skipping.", "log")
                continue
            # v0.7.2: O(1) src lookup + dst check via _passage_dict
            _src_dict_body = _passage_dict.get(src_name)
            if _src_dict_body is not None:
                _src_tags_m = re.search(r'tags="([^"]*)', _passage_meta[src_name][0])
                src_tags = _src_tags_m.group(1) if _src_tags_m else ''
                src_body = _src_dict_body
            else:
                src_body = None; src_tags = ''
                if passage_registry and passage_names_seen and src_name in passage_names_seen:
                    _ridx = passage_names_seen[src_name]
                    src_body = passage_registry[_ridx].get('body', '')
                    src_tags = passage_registry[_ridx].get('tags', '')
                if src_body is None:
                    handle_output(f"Clone Passage: source '{src_name}' not found", "log")
                    handle_output(f"Clone Passage: source '{src_name}' not found", "failed")
                    replacements_failed += 1
                    failed_mods.append(mod_file)
                    continue
            if dst_name in _passage_dict:
                handle_output(f"Clone Passage: destination '{dst_name}' already exists, skipping.", "log")
                continue
            # Register clone in passage_registry so Phase 7 injects it
            if dst_name not in (passage_names_seen or {}):
                _clone_rec = {
                    'name':     dst_name,
                    'body':     src_body,
                    'tags':     src_tags,
                    'guards':   {},
                    'mod_file': mod_file,
                    'format':   'full',
                }
                if passage_names_seen is not None:
                    passage_names_seen[dst_name] = len(passage_registry)
                if passage_registry is not None:
                    passage_registry.append(_clone_rec)
                handle_output(f"Clone Passage: queued '{src_name}' -> '{dst_name}' for Phase 7 injection", "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                handle_output(f"Clone Passage: '{dst_name}' already in registry, skipping.", "log")

        elif kind == 'wrap_passage':
            # v0.7.1: Inject content at the start (before) or end (after) of a
            # passage body without touching its content.  Like Hook but for passages.
            psg_name = name
            timing   = entry['timing']
            body     = entry['body']
            guards   = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Wrap Passage [{psg_name}]', skipping.", "log")
                continue
            # v0.7.2 Option 1: O(1) passage lookup via dict
            _wp_body = _passage_dict.get(psg_name)
            if _wp_body is not None:
                _wp_meta = _passage_meta[psg_name]
                _wp_open, _wp_abs_start, _wp_abs_end = _wp_meta
                class _WPMatch:
                    def __init__(self, opentag, body, abs_start):
                        self._open = opentag; self._body = body; self._abs_start = abs_start
                    def group(self, g):
                        if g == 1: return self._open
                        if g == 2: return self._body
                        return '</tw-passagedata>'
                    def start(self, g=0):
                        return self._abs_start + len(self._open) if g == 2 else self._abs_start
                    def end(self, g=0):
                        return self._abs_start + len(self._open) + len(self._body) if g == 2 else self._abs_start + len(self._open) + len(self._body) + len('</tw-passagedata>')
                wp_m = _WPMatch(_wp_open, _wp_body, _wp_abs_start)
            else:
                wp_pat = _get_compiled(
                    r'(<tw-passagedata[^>]*name="' + re.escape(psg_name) + r'"[^>]*>)'
                    r'(.*?)(</tw-passagedata>)',
                    re.DOTALL
                )
                wp_m = wp_pat.search(html_content)
            if not wp_m:
                handle_output(f"Wrap Passage: passage '{psg_name}' not found", "log")
                handle_output(f"Wrap Passage: passage '{psg_name}' not found", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            esc_body = escape_twine_tags(body)
            if esc_body in wp_m.group(2):
                handle_output(f"Wrap Passage: already applied for '{psg_name}', skipping.", "log")
                continue
            if timing == 'before':
                new_psg_body = esc_body + '\n' + wp_m.group(2)
            else:
                new_psg_body = wp_m.group(2) + '\n' + esc_body
            html_content = (
                html_content[:wp_m.start(2)]
                + new_psg_body
                + html_content[wp_m.end(2):]
            )
            handle_output(f"Wrap Passage [{timing}]: wrapped '{psg_name}'", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

        elif kind == 'replace_in_all_passages':
            # v0.7.1: Apply an anchor replacement to every passage with a given tag.
            tag_name   = name
            anchor     = _normalize_anchor(entry['anchor'])
            new_body   = entry['body']
            guards     = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Replace In All Passages [{tag_name}]', skipping.", "log")
                continue
            # v0.7.2: scan _passage_meta open tags for tag; O(1) body lookup
            tagged_passages = [
                pname for pname, (open_tag, _, _) in _passage_meta.items()
                if (' ' + tag_name + ' ') in open_tag
                or ('"' + tag_name + '"') in open_tag
                or ('"' + tag_name + ' ') in open_tag
                or (' ' + tag_name + '"') in open_tag
            ]
            if not tagged_passages:
                handle_output(f"Replace In All Passages [{tag_name}]: no passages with that tag found", "log")
                continue
            riap_applied = 0
            for tp_name in tagged_passages:
                tp_body = _passage_dict.get(tp_name)
                if tp_body is None:
                    continue
                _tp_open, _tp_abs_start, _tp_abs_end = _passage_meta[tp_name]
                tp_body_start = _tp_abs_start + len(_tp_open)
                tp_body_end   = _tp_abs_end - len('</tw-passagedata>')
                anchor_pat = re.escape(anchor).replace(r'\n', r'\s*\n\s*')
                if not _fast_search(anchor_pat, tp_body):
                    continue
                if re.search(re.escape(new_body), tp_body):
                    handle_output(f"Replace In All Passages [{tag_name}]: already applied in '{tp_name}', skipping.", "log")
                    continue
                new_tp_body = re.sub(anchor_pat, lambda _: new_body, tp_body, count=1)
                html_content = (
                    html_content[:tp_body_start]
                    + new_tp_body
                    + html_content[tp_body_end:]
                )
                _passage_dict[tp_name] = new_tp_body
                riap_applied += 1
            if riap_applied:
                handle_output(f"Replace In All Passages [{tag_name}]: applied to {riap_applied}/{len(tagged_passages)} passages", "log")
                replacements_made += 1
                successful_mods.append(mod_file)
            else:
                handle_output(f"Replace In All Passages [{tag_name}]: anchor not found in any tagged passage", "log")

        elif kind == 'add_storyvar':
            # v0.7.1: Initialize variable in StoryInit AND mark it save-persistent
            # via setup.saveStateFields (SugarCube's State.variables persistence list).
            varname = name
            value   = entry.get('value', 'undefined')
            guards  = entry.get('guards', {})
            if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(f"Guard condition not met for 'Add StoryVar [{varname}]', skipping.", "log")
                continue
            # v0.7.2: O(1) StoryInit lookup via _passage_dict
            init_body = _passage_dict.get('StoryInit')
            if init_body is None:
                handle_output(f"Add StoryVar: StoryInit passage not found for '{varname}'", "log")
                handle_output(f"Add StoryVar: StoryInit passage not found for '{varname}'", "failed")
                replacements_failed += 1
                failed_mods.append(mod_file)
                continue
            var_pat = _get_compiled(r'\$' + re.escape(varname) + r'\b')
            if not var_pat.search(init_body):
                set_line = f'&lt;&lt;set ${varname} to {value}&gt;&gt;'
                _si_open, _si_abs_start, _ = _passage_meta['StoryInit']
                insert_pos = _si_abs_start + len(_si_open)
                html_content = html_content[:insert_pos] + set_line + '\n' + html_content[insert_pos:]
                _passage_dict['StoryInit'] = set_line + '\n' + init_body
                handle_output(f"Add StoryVar: injected '${varname}' into StoryInit", "log")
            else:
                handle_output(f"Add StoryVar: '{varname}' already in StoryInit, skipping init.", "log")
            # Step 2: Inject into setup.saveStateFields via Add Javascript pattern
            # Register as a JS snippet into js_registry so it lands in the script block
            _ssf_snippet = (
                f"if (typeof setup.saveStateFields === 'undefined') {{ setup.saveStateFields = []; }}\n"
                f"if (setup.saveStateFields.indexOf('{varname}') === -1) {{ setup.saveStateFields.push('{varname}'); }}"
            )
            ssf_check = f"saveStateFields.indexOf('{varname}')"
            if ssf_check not in html_content:
                if js_registry is not None:
                    js_registry.append({'body': _ssf_snippet, 'guards': {}, 'mod_file': mod_file})
                handle_output(f"Add StoryVar: registered '{varname}' in setup.saveStateFields", "log")
            else:
                handle_output(f"Add StoryVar: '{varname}' already in saveStateFields, skipping.", "log")
            replacements_made += 1
            successful_mods.append(mod_file)

    # v0.7.2 Option 1: Phase 4 mutated html_content -- rebuild passage_dict
    # before Phase 5 so Hook bodies that reference passage content are correct.
    _passage_dict, _passage_meta, _script_block, _max_pid = _split_html(html_content)

    flush_logs()
    # ---- Hook [] entries (function wrapping) ----
    for entry in mod_hook_list:
        name     = entry['name']
        timing   = entry['timing']
        hook_body = entry['body']
        mod_file = entry['mod_file']
        guards = entry.get('guards', {})
        if not _check_guards(guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
            handle_output(f"Guard condition not met for 'Hook [{name}]', skipping.", "log")
            continue

        # Find the function -- supports both assignment and declaration styles
        pat = _get_compiled(
            r'(' + re.escape(name) + r'\s*[=:]\s*function\s*\(([^)]*)\))'
            r'|(function\s+' + re.escape(name) + r'\s*\(([^)]*)\))',
            re.DOTALL
        )
        m = pat.search(html_content)
        if not m:
            handle_output(f"Hook: no match for '{name}'", "log")
            handle_output(f"Hook: no match for '{name}'", "failed")
            replacements_failed += 1
            failed_mods.append(mod_file)
            continue

        # Extract params from whichever style matched
        params = (m.group(2) if m.group(2) is not None else m.group(4) or '').strip()
        wrapper_var = name.replace('.', '_').replace('[', '_').replace(']', '_') + '__orig'

        # --- v0.7.4: Parameter destructuring injection ---
        # Parse the original function's parameter list into clean bare names
        # (strips default values and rest-spread prefixes so the destructuring
        # assignment is always valid JS regardless of the original signature).
        # Injects "const [p1, p2, ...] = arguments;" at the top of the wrapper
        # body so hook authors can reference original parameter names by name.
        _param_names = []
        if params:
            for _p in params.split(','):
                _pname = _p.strip().lstrip('...').split('=')[0].strip()
                if _pname:
                    _param_names.append(_pname)
        _param_destructure = (
            f"    const [{', '.join(_param_names)}] = arguments;\n"
            if _param_names else ""
        )

        # --- v0.7.4: Local-variable static analysis warning ---
        # Collect local variable and parameter names declared inside the
        # original function body.  Warn if the hook body references any of them
        # -- those names are out of scope in the wrapper and will cause a
        # ReferenceError at runtime.
        _orig_body_start = html_content.find('{', m.end())
        _orig_body_end   = _bracket_match(html_content, _orig_body_start, '{', '}') if _orig_body_start != -1 else -1
        if _orig_body_start != -1 and _orig_body_end != -1:
            _orig_body = html_content[_orig_body_start:_orig_body_end]
            # Find all identifiers bound as locals (let/const/var declarations)
            _local_decl_names = set(re.findall(
                r'\b(?:let|const|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)', _orig_body
            ))
            # Exclude params (those ARE injected via destructuring above)
            _local_decl_names -= set(_param_names)
            # Check hook body for any of these names as whole-word identifiers
            _hook_refs_locals = [
                _lv for _lv in sorted(_local_decl_names)
                if re.search(r'\b' + re.escape(_lv) + r'\b', hook_body)
            ]
            if _hook_refs_locals:
                _warn_msg = (
                    f"HOOK WARNING: Hook [{name}] ({timing}) in {mod_file} -- "
                    f"hook body references local variable(s) of the original function "
                    f"that are out of scope in the wrapper: "
                    f"{', '.join(_hook_refs_locals)}. "
                    f"These will cause a ReferenceError at runtime. "
                    f"Declare them independently inside the hook body."
                )
                handle_output(_warn_msg, "alllogs")

        if timing == 'before':
            wrapper = (
                f"var {wrapper_var} = {name};\n"
                f"{name} = function() {{\n"
                f"{_param_destructure}"
                f"    {hook_body}\n"
                f"    return {wrapper_var}.apply(this, arguments);\n"
                f"}};\n"
            )
        elif timing == 'after':
            wrapper = (
                f"var {wrapper_var} = {name};\n"
                f"{name} = function() {{\n"
                f"{_param_destructure}"
                f"    var _result = {wrapper_var}.apply(this, arguments);\n"
                f"    {hook_body}\n"
                f"    return _result;\n"
                f"}};\n"
            )
        else:  # around -- hook_body receives _result and may replace it
            # around: body runs after the original call and has full control
            # over _result. Use: return <expr>; to replace the return value.
            # If hook_body does not return, original _result is returned.
            wrapper = (
                f"var {wrapper_var} = {name};\n"
                f"{name} = function() {{\n"
                f"{_param_destructure}"
                f"    var _result = {wrapper_var}.apply(this, arguments);\n"
                f"    (function() {{ {hook_body} }}).call(this);\n"
                f"    return _result;\n"
                f"}};\n"
            )

        if wrapper_var in html_content:
            # v0.7.3: Hook conflict fix -- a second+ mod hooked the same function.
            # Instead of silently dropping it, append the new body inside the
            # existing wrapper so all mods fire in load order.
            # Locate the existing wrapper block and inject before its closing '};'
            wv_idx = html_content.find(wrapper_var)
            # Walk to the wrapper function's closing brace
            _wb_open = html_content.find('{', wv_idx)
            if _wb_open != -1:
                _wb_close = _bracket_match(html_content, _wb_open, '{', '}')
                if _wb_close != -1:
                    extra = f"\n    // Hook ({timing}) [{mod_file}]\n    {hook_body}"
                    html_content = (
                        html_content[:_wb_close]
                        + extra
                        + html_content[_wb_close:]
                    )
                    handle_output(
                        f"Hook ({timing}): appended additional body for '{name}' from {mod_file}",
                        "log"
                    )
                    replacements_made += 1
                    successful_mods.append(mod_file)
                    continue
            handle_output(f"Hook: already applied for '{name}', skipping.", "log")
            continue

        # Insert the wrapper right after the original function's closing brace
        brace_open_pos = html_content.find('{', m.end())
        if brace_open_pos == -1:
            handle_output(f"Hook: could not find opening brace for '{name}'", "log")
            replacements_failed += 1
            failed_mods.append(mod_file)
            continue
        brace_close_pos = _bracket_match(html_content, brace_open_pos, '{', '}')
        if brace_close_pos == -1:
            handle_output(f"Hook: could not find body end for '{name}'", "log")
            replacements_failed += 1
            failed_mods.append(mod_file)
            continue
        insert_pos = brace_close_pos + 1
        html_content = html_content[:insert_pos] + '\n' + wrapper + html_content[insert_pos:]
        handle_output(f"Hook ({timing}): wrapped '{name}'", "log")
        replacements_made += 1
        successful_mods.append(mod_file)

    # ---- v0.6.0: Passage registry inner replacement sweep ----
    # In v0.5.3, Add Passage: blocks were converted to Replace:/With: pairs and
    # injected into the HTML during the Replace: loop.  Other Replace: entries
    # targeting content inside those passages could find their targets because the
    # passages were already present in the HTML.
    #
    # In v0.6.0, Add Passage: blocks go to passage_registry and are injected AFTER
    # the Replace: loop.  This means Replace: entries that target content inside a
    # registry passage body (same-mod or cross-mod) will fail with "No match found".
    #
    # Fix: Before registry injection, sweep all unmatched Replace: entries against
    # passage_registry bodies and apply matches directly into the registry records.
    if passage_registry and _failed_replace_keys:
        _psg_inner_applied = 0
        _psg_inner_resolved = set()
        _resolved_mods = set()
        for search_key in list(_failed_replace_keys):
            if search_key not in mod_dict:
                continue
            search_entry = mod_dict[search_key]
            search_new, search_guards = search_entry
            # Build all plausible forms of the search key:
            # - search_key itself (may be HTML-escaped &lt;&lt; form from passage Replace:)
            # - unescaped form (raw << >> for matching against full-format passage bodies)
            unescaped_key = search_key.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'")
            for psg_entry in passage_registry:
                # Skip early-injected entries -- their body is already in
                # html_content so the Replace: should target it there directly,
                # not in the stale pre-escape registry body.
                if psg_entry.get('early_injected'):
                    continue
                psg_body = psg_entry['body']
                # Try escaped key first (matches shorthand passage bodies),
                # then unescaped key (matches full-format raw passage bodies).
                matched_key = None
                inject_new = None
                if search_key in psg_body:
                    matched_key = search_key
                    inject_new = search_new
                elif unescaped_key != search_key and unescaped_key in psg_body:
                    matched_key = unescaped_key
                    # Unescape the With: body too so it's consistent with the raw passage
                    inject_new = search_new.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'")
                if matched_key is not None:
                    psg_entry['body'] = psg_body.replace(matched_key, inject_new, 1)
                    _psg_inner_applied += 1
                    _psg_inner_resolved.add(search_key)
                    handle_output(
                        f"Passage registry inner replacement: applied '{search_key[:60]}' "
                        f"into passage '{psg_entry['name']}' body",
                        "log"
                    )
                    # Remove from mod_dict so it doesn't produce "No match found"
                    mod_dict.pop(search_key, None)
                    _failed_replace_keys.discard(search_key)
                    # Remove from mod_file_indexes
                    source_mod = key_to_mod.get(search_key) if key_to_mod else None
                    if source_mod:
                        _resolved_mods.add(source_mod)
                    if source_mod and source_mod in mod_file_indexes:
                        try:
                            mod_file_indexes[source_mod].remove(search_key)
                        except ValueError:
                            pass
                    break
        if _psg_inner_applied:
            handle_output(
                f"Passage registry inner replacements: applied {_psg_inner_applied} entries",
                "log"
            )
            # Remove resolved mods from failed_mods if all their Replace: failures
            # were resolved by the sweep and no remaining _failed_replace_keys belong
            # to that mod.
            for _rmod in list(_resolved_mods):
                if _rmod not in failed_mods:
                    continue
                still_failing = any(
                    key_to_mod.get(k) == _rmod
                    for k in _failed_replace_keys
                ) if (key_to_mod and _failed_replace_keys) else False
                if not still_failing:
                    failed_mods = [m for m in failed_mods if m != _rmod]
                    if _rmod not in successful_mods:
                        successful_mods.append(_rmod)
            # Decrement replacements_failed for each key resolved by this sweep.
            _replacements_resolved += len(_psg_inner_resolved)
            # Annotate stale "No match found" entries in FailsPatchLog.
            # These were written during the Replace: loop before the sweep ran.
            # Rather than deleting them (which could hide real issues), mark them
            # as resolved so the log shows the sweep handled them.
            try:
                with open(faillog_file, 'r', encoding='utf-8') as f:
                    fail_lines = f.read()
                modified = False
                for search_key in _psg_inner_resolved:
                    marker = f"No match found for '{search_key[:60]}"
                    if marker in fail_lines:
                        fail_lines = fail_lines.replace(
                            f"No match found for '{search_key}",
                            f"RESOLVED by passage registry sweep -- No match found for '{search_key}"
                        )
                        modified = True
                if modified:
                    with open(faillog_file, 'w', encoding='utf-8') as f:
                        f.write(fail_lines)
            except (FileNotFoundError, OSError):
                pass

    # Add Function summary
    af_total_skipped = af_skipped_guard + af_skipped_exists
    handle_output(
        f"Add Function: injected {af_injected} functions ({af_lines_total} lines total), "
        f"skipped {af_total_skipped} ({af_skipped_guard} guard failures, {af_skipped_exists} already exist)",
        "log"
    )

    # ---- v0.6.0: Passage registry Insert After/Before sweep ----
    # Same problem as Replace: entries above.  Insert After/Before directives
    # that target content inside Add Passage bodies fail in Phase 4 because
    # the passages are still in the registry.  Sweep failed IA/IB entries
    # against passage_registry bodies and apply matches directly.
    if passage_registry and _failed_ia_ib_entries:
        _ia_ib_applied = 0
        _ia_ib_resolved = []
        for entry in list(_failed_ia_ib_entries):
            anchor = entry['name']
            body = entry['body']
            ia_kind = entry['kind']
            ia_mod = entry.get('mod_file', '')
            # Build unescaped form of anchor for matching raw passage bodies
            unescaped_anchor = anchor.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace("&#39;", "'")
            for psg_entry in passage_registry:
                # Skip early-injected entries -- their body is already in
                # html_content so IA/IB should target it there directly.
                if psg_entry.get('early_injected'):
                    continue
                psg_body = psg_entry['body']
                # Try anchor as-is first, then unescaped
                matched_anchor = None
                inject_body = body
                if anchor in psg_body:
                    matched_anchor = anchor
                elif unescaped_anchor != anchor and unescaped_anchor in psg_body:
                    matched_anchor = unescaped_anchor
                    inject_body = body.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&').replace("&#39;", "'")
                if matched_anchor is not None:
                    # Duplicate check
                    anchor_pos = psg_body.find(matched_anchor)
                    if ia_kind == 'insert_after':
                        check_start = anchor_pos + len(matched_anchor)
                        if inject_body in psg_body[check_start:check_start + len(inject_body) + 2]:
                            handle_output(
                                f"Registry IA/IB sweep: already applied '{anchor[:50]}' in '{psg_entry['name']}', skipping.",
                                "log"
                            )
                            break
                        psg_entry['body'] = psg_body[:check_start] + '\n' + inject_body + psg_body[check_start:]
                    else:  # insert_before
                        if inject_body in psg_body[max(0, anchor_pos - len(inject_body) - 2):anchor_pos + 2]:
                            handle_output(
                                f"Registry IA/IB sweep: already applied '{anchor[:50]}' in '{psg_entry['name']}', skipping.",
                                "log"
                            )
                            break
                        psg_entry['body'] = psg_body[:anchor_pos] + inject_body + '\n' + psg_body[anchor_pos:]
                    label = 'Insert After' if ia_kind == 'insert_after' else 'Insert Before'
                    _ia_ib_applied += 1
                    _ia_ib_resolved.append(entry)
                    handle_output(
                        f"Registry IA/IB sweep: applied {label} '{anchor[:50]}' into passage '{psg_entry['name']}'",
                        "log"
                    )
                    break
        if _ia_ib_applied:
            handle_output(
                f"Registry IA/IB sweep: applied {_ia_ib_applied} Insert After/Before entries into passage registry",
                "log"
            )
            # Mirror Phase 6 Replace: sweep: remove mods whose IA/IB failures were
            # all resolved from failed_mods, promote to successful_mods if not already
            # there, and decrement the resolved counter so the summary stays accurate.
            _ia_ib_resolved_mods = set()
            for entry in _ia_ib_resolved:
                ia_mod = entry.get('mod_file', '')
                if ia_mod:
                    _ia_ib_resolved_mods.add(ia_mod)
            for _rmod in _ia_ib_resolved_mods:
                if _rmod not in failed_mods:
                    continue
                # Only promote if this mod has no remaining unresolved IA/IB failures.
                still_failing = any(
                    e.get('mod_file') == _rmod
                    for e in _failed_ia_ib_entries
                    if e not in _ia_ib_resolved
                )
                if not still_failing:
                    failed_mods = [m for m in failed_mods if m != _rmod]
                    if _rmod not in successful_mods:
                        successful_mods.append(_rmod)
            _replacements_resolved += len(_ia_ib_resolved)
            # Annotate stale failure entries in FailsPatchLog
            try:
                with open(faillog_file, 'r', encoding='utf-8') as f:
                    fail_lines = f.read()
                modified = False
                for entry in _ia_ib_resolved:
                    anchor = entry['name']
                    label = 'Insert After' if entry['kind'] == 'insert_after' else 'Insert Before'
                    marker = f"{label}: no match for '{anchor[:60]}"
                    if marker in fail_lines:
                        fail_lines = fail_lines.replace(
                            f"{label}: no match for '{anchor}",
                            f"RESOLVED by registry IA/IB sweep -- {label}: no match for '{anchor}"
                        )
                        modified = True
                if modified:
                    with open(faillog_file, 'w', encoding='utf-8') as f:
                        f.write(fail_lines)
            except (FileNotFoundError, OSError):
                pass

    flush_logs()
    # ---- v0.6.0: Registry injection phases ----
    # After all mod_dict, mod_func_list, and mod_hook_list entries are applied,
    # inject registry entries in deterministic mod-load order.

    # -- Add Javascript injection --
    if js_registry:
        js_anchor = '</script><tw-passagedata'
        js_anchor_idx = html_content.find(js_anchor)
        if js_anchor_idx == -1:
            handle_output("Add Javascript: script anchor not found in HTML", "alllogs")
        else:
            js_injected = 0
            js_skipped = 0
            js_lines_total = 0
            js_parts = []
            for js_entry in js_registry:
                js_guards = js_entry.get('guards', {})
                if not _check_guards(js_guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                    handle_output(
                        f"Add Javascript: skipped block from {js_entry['mod_file']} -- guard condition not met",
                        "log"
                    )
                    js_skipped += 1
                    continue
                js_body = js_entry['body']
                js_parts.append(js_body)
                line_count = js_body.count('\n') + 1
                js_lines_total += line_count
                handle_output(
                    f"Add Javascript: injected block from {js_entry['mod_file']} ({line_count} lines)",
                    "log"
                )
                js_injected += 1
                successful_mods.append(js_entry['mod_file'])
            if js_parts:
                js_block = '\n' + '\n'.join(js_parts) + '\n'
                # Re-find anchor (may have shifted from earlier patches)
                js_anchor_idx = html_content.find(js_anchor)
                if js_anchor_idx != -1:
                    html_content = html_content[:js_anchor_idx] + js_block + html_content[js_anchor_idx:]
                    replacements_made += 1
            handle_output(
                f"Add Javascript: injected {js_injected} blocks ({js_lines_total} lines total), skipped {js_skipped}",
                "log"
            )

    # -- Add CSS injection --
    if css_registry:
        css_anchor = '</style><script'
        css_anchor_idx = html_content.find(css_anchor)
        if css_anchor_idx == -1:
            handle_output("Add CSS: style anchor not found in HTML", "alllogs")
        else:
            css_injected = 0
            css_skipped = 0
            css_lines_total = 0
            css_parts = []
            for css_entry in css_registry:
                css_guards = css_entry.get('guards', {})
                if not _check_guards(css_guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                    handle_output(
                        f"Add CSS: skipped block from {css_entry['mod_file']} -- guard condition not met",
                        "log"
                    )
                    css_skipped += 1
                    continue
                css_body = css_entry['body']
                css_parts.append(css_body)
                line_count = css_body.count('\n') + 1
                css_lines_total += line_count
                handle_output(
                    f"Add CSS: injected block from {css_entry['mod_file']} ({line_count} lines)",
                    "log"
                )
                css_injected += 1
                successful_mods.append(css_entry['mod_file'])
            if css_parts:
                css_block = '\n' + '\n'.join(css_parts) + '\n'
                css_anchor_idx = html_content.find(css_anchor)
                if css_anchor_idx != -1:
                    html_content = html_content[:css_anchor_idx] + css_block + html_content[css_anchor_idx:]
                    replacements_made += 1
            handle_output(
                f"Add CSS: injected {css_injected} blocks ({css_lines_total} lines total), skipped {css_skipped}",
                "log"
            )

    # -- Add Events injection --
    if events_registry:
        events_anchor = "setup.Events.db =\n["
        events_anchor_idx = html_content.find(events_anchor)
        if events_anchor_idx == -1:
            handle_output("Add Events: events anchor not found in HTML", "alllogs")
        else:
            ev_injected = 0
            ev_skipped = 0
            ev_parts = []
            for ev_entry in events_registry:
                ev_guards = ev_entry.get('guards', {})
                if not _check_guards(ev_guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                    handle_output(
                        f"Add Events: skipped block from {ev_entry['mod_file']} -- guard condition not met",
                        "log"
                    )
                    ev_skipped += 1
                    continue
                ev_body = ev_entry['body']
                ev_parts.append(ev_body)
                entry_count = ev_body.count('{')
                handle_output(
                    f"Add Events: injected block from {ev_entry['mod_file']} (~{entry_count} entries)",
                    "log"
                )
                ev_injected += 1
                successful_mods.append(ev_entry['mod_file'])
            if ev_parts:
                ev_block = '\n' + '\n'.join(ev_parts)
                # Re-find anchor and insert AFTER it (append_targets behavior)
                events_anchor_idx = html_content.find(events_anchor)
                if events_anchor_idx != -1:
                    insert_after = events_anchor_idx + len(events_anchor)
                    html_content = html_content[:insert_after] + ev_block + html_content[insert_after:]
                    replacements_made += 1
            handle_output(
                f"Add Events: injected {ev_injected} blocks, skipped {ev_skipped}",
                "log"
            )

    # -- Refresh _script_block before passage guard checks (v0.7.2 fix) --
    # Add Javascript (above) injects into html_content AFTER the _split_html rebuild
    # at the Phase 4/5 boundary.  IfFunctionExists guards on Add Passage entries
    # search _script_block -- if a function is defined via Add Javascript rather than
    # Add Function, it lands in html_content here but _script_block is stale and the
    # guard fails even though the function is present.  Re-extract now so all
    # Phase 7 guard checks see the fully-populated script block.
    # Uses same findall-join strategy as _split_html to cover all script blocks.
    _sb_p7 = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL)
    if _sb_p7:
        _script_block = '\n'.join(_sb_p7)

    # -- Add Passage registry injection (Part A.4) --
    if passage_registry:
        psg_injected = 0
        psg_skipped_guard = 0
        psg_skipped_vanilla = 0
        psg_skipped_malformed = 0
        psg_parts = []

        for psg_entry in passage_registry:
            psg_name = psg_entry['name']
            psg_guards = psg_entry.get('guards', {})

            # Skip entries already injected during Delete Block early-injection
            if psg_entry.get('early_injected'):
                handle_output(
                    f"Add Passage: skipped '{psg_name}' -- already early-injected by Delete Block",
                    "log"
                )
                psg_skipped_vanilla += 1
                continue

            # Step 4.2a: Evaluate guards at injection time
            if not _check_guards(psg_guards, html_content, loaded_mod_files, passage_registry=passage_registry, passage_dict=_passage_dict, passage_meta=_passage_meta, script_block=_script_block):
                handle_output(
                    f"Add Passage: skipped '{psg_name}' -- guard condition not met",
                    "log"
                )
                psg_skipped_guard += 1
                continue

            # Step 4.2b: Check if name already exists in vanilla HTML or from accumulator path
            if psg_name in _original_passage_names:
                handle_output(
                    f"Add Passage: skipped '{psg_name}' -- already exists in vanilla HTML",
                    "log"
                )
                psg_skipped_vanilla += 1
                continue

            # v0.7.2: O(1) existence check via passage_dict
            if psg_name in _passage_dict:
                handle_output(
                    f"Add Passage: skipped '{psg_name}' -- already injected via accumulator path",
                    "log"
                )
                psg_skipped_vanilla += 1
                continue

            # Step 4.2c-d: Build the passage tag and escape the body
            psg_body = psg_entry['body']
            psg_tags = psg_entry.get('tags', '')
            psg_fmt = psg_entry.get('format', 'shorthand')

            # Escaping chain per spec:
            # Shorthand: escape_html_between_tags -> escape_twine_tags -> auto_escape_passage_bodies
            # Full format: escape_html_between_tags -> escape_twine_tags -> auto_escape_passage_bodies
            # escape_twine_tags is safe on pre-escaped content (only matches actual << >>
            # pairs, not &lt;&lt; &gt;&gt;). Required for mods like SE that use full format
            # with raw SugarCube macros (<<script>>, <<timed>>) without <e> tags.
            # Both shorthand and full format use the same escaping chain.
            psg_body = escape_html_between_tags(psg_body)
            psg_body = escape_twine_tags(psg_body)
            psg_body = auto_escape_passage_bodies(psg_body)

            psg_tag = (
                f'<tw-passagedata pid="auto" name="{psg_name}" tags="{psg_tags}" '
                f'position="100,100" size="100,100">'
                f'{psg_body}'
                f'</tw-passagedata>'
            )

            # Step 4.2e: Tag balance validation on the escaped body
            _psg_warnings = check_injection_tag_balance(
                psg_tag, 0, f"Add Passage [{psg_name}] from {psg_entry['mod_file']}"
            )
            for _pw in _psg_warnings:
                handle_output(_pw, 'alllogs')

            psg_parts.append(psg_tag)
            handle_output(
                f"Add Passage: injected '{psg_name}' (from {psg_entry['mod_file']})",
                "log"
            )
            psg_injected += 1
            successful_mods.append(psg_entry['mod_file'])

        # Step 4.3-4: Inject passages into DOM or raw string
        if psg_parts:
            if _html_layer.bs4_available:
                # Re-sync DOM from html_content (captures all earlier directive changes)
                _html_layer = KittyHTMLLayer(html_content)
                for _psg_tag_str in psg_parts:
                    import re as _re
                    _nm = _re.search(r'name="([^"]+)"', _psg_tag_str)
                    _tg = _re.search(r'tags="([^"]*)"', _psg_tag_str)
                    _bd = _re.search(r'<tw-passagedata[^>]*>(.*?)</tw-passagedata>', _psg_tag_str, _re.DOTALL)
                    if _nm and _bd:
                        _html_layer.add_passage(
                            name=_nm.group(1),
                            body=_bd.group(1),
                            tags=_tg.group(1) if _tg else ""
                        )
                html_content = _html_layer.serialize()
                replacements_made += 1
            else:
                psg_block = '\n' + '\n'.join(psg_parts) + '\n'
                storydata_close_idx = html_content.find('</tw-storydata>')
                if storydata_close_idx != -1:
                    html_content = html_content[:storydata_close_idx] + psg_block + html_content[storydata_close_idx:]
                    replacements_made += 1
                else:
                    handle_output("Add Passage: </tw-storydata> anchor not found in HTML", "alllogs")

        psg_total_skipped = psg_skipped_guard + psg_skipped_vanilla + psg_skipped_malformed
        handle_output(
            f"Add Passage: injected {psg_injected} passages, skipped {psg_total_skipped} "
            f"({psg_skipped_guard} guard failures, {psg_skipped_vanilla} vanilla conflicts, "
            f"{psg_skipped_malformed} malformed)",
            "log"
        )

    # ---- Conflict detection report ----
    warned_mods = set()
    for target, entries in conflict_map.items():
        if len(entries) > 1:
            mods_involved = list({e[0] for e in entries})
            kinds_involved = [f"{e[0]} ({e[1]})" for e in entries]
            msg = (
                f"CONFLICT DETECTED: Multiple mods target '{target}':\n" +
                "\n".join(f"\t{k}" for k in kinds_involved)
            )
            handle_output(msg, "alllogs")
            handle_output(msg, "failed")
            for _wm in mods_involved:
                warned_mods.add(_wm)

    # ---- v0.7.1: Directive ordering warnings ----
    # Warn when two IA/IB directives from different mods target the same anchor.
    # Same-anchor ordering is load-order dependent -- flagging it helps authors
    # use [ONCE] or different anchors to make the interaction explicit.
    _ia_anchor_mods: dict = {}
    for _entry in mod_func_list:
        if _entry.get('kind') in ('insert_after', 'insert_before'):
            _anc = _entry.get('name', '')
            _mf  = _entry.get('mod_file', '')
            _ia_anchor_mods.setdefault(_anc, []).append(_mf)
    for _anc, _mods_list in _ia_anchor_mods.items():
        if len(set(_mods_list)) > 1:
            _mods_str = ', '.join(os.path.basename(m) for m in dict.fromkeys(_mods_list))
            handle_output(
                f"ORDERING WARNING: Multiple mods inject at anchor '{_anc[:80]}' "
                f"-- load-order determines injection sequence: {_mods_str}. "
                f"Consider [ONCE] modifier if only one injection is intended.",
                "alllogs"
            )

    # ---- v0.7.1: Conflict map JSON output ----
    # Writes ConflictMap.json to the logs folder so external tools and
    # KittyToolbench can visualise the full collision surface of the mod stack.
    try:
        import json as _json
        _cmap_out = {}
        for _tgt, _entries in conflict_map.items():
            if len(_entries) > 1:
                _cmap_out[_tgt] = [{'mod': e[0], 'kind': e[1]} for e in _entries]
        _cmap_path = os.path.join(logs_folder, 'ConflictMap.json')
        with open(_cmap_path, 'w', encoding='utf-8') as _cf:
            _json.dump(_cmap_out, _cf, indent=2)
        handle_output(f"Conflict map written: {len(_cmap_out)} conflict(s) -> ConflictMap.json", "log")
    except Exception as _cmap_err:
        handle_output(f"ConflictMap.json write failed: {_cmap_err}", "log")

    # ---- Pid renormalization ----
    # Renumber all pids sequentially in document order after all patches are applied.
    # SugarCube uses passage names (not pids) for all lookups, so this is safe.
    # Fixes Twine-editor cosmetic warnings and resolves any pid collisions between mods.
    if _html_layer.bs4_available:
        # Sync any raw-string changes from text-search directives back into the DOM
        # before renormalizing, so the layer sees the final passage set.
        _html_layer = KittyHTMLLayer(html_content)
        _psg_count = _html_layer.renormalize_pids()
        _html_layer.set_watermark("v0.7.1")
        html_content = _html_layer.serialize()
        handle_output(f"Pid renormalization complete (DOM). Total passages: {_psg_count}", "log")
    else:
        html_content = _renormalize_pids(html_content)
        handle_output(f"Pid renormalization complete. Total passages: {html_content.count('<tw-passagedata')}", "log")

    # ---- HTML integrity checks ----
    # tw-passagedata tag balance
    open_passages  = html_content.count('<tw-passagedata')
    close_passages = html_content.count('</tw-passagedata>')
    if open_passages != close_passages:
        handle_output(
            f"WARNING: Unbalanced <tw-passagedata> tags ({open_passages} open vs {close_passages} close)",
            "alllogs"
        )
        find_passage_imbalance(html_content)

    # Twine macro balance checks (v0.7.0: per-passage when BS4 available -- plan 1.8)
    if _html_layer.bs4_available:
        # Re-sync layer from final html_content (after PID renorm serialized it)
        _balance_layer = KittyHTMLLayer(html_content)
        _macro_warnings = 0
        for _bpname in _balance_layer.all_passage_names():
            _bpbody = _balance_layer.get_passage_body(_bpname) or ''
            for _open_tok, _close_tok in _TWINE_PAIRS:
                _opens  = _count_twine_open(_bpbody, _open_tok)
                _closes = _bpbody.count(_close_tok)
                if _opens != _closes:
                    handle_output(
                        f"WARNING: Unbalanced {_open_tok}>> in passage '{_bpname}' "
                        f"({_opens} open vs {_closes} close, diff={_opens - _closes:+d})",
                        "alllogs"
                    )
                    _macro_warnings += 1
        if _macro_warnings == 0:
            handle_output("Macro balance check: all passages OK", "log")
    else:
        # Fallback: global check with no passage attribution
        for open_tok, close_tok in _TWINE_PAIRS:
            open_count  = _count_twine_open(html_content, open_tok)
            close_count = html_content.count(close_tok)
            if open_count != close_count:
                handle_output(
                    f"WARNING: Unbalanced {open_tok}>> macros globally "
                    f"({open_count} open vs {close_count} close, diff={open_count - close_count:+d})",
                    "alllogs"
                )

    # Log summary
    if replacements_made == 0:
        handle_output("No matches found for any mod lines.", "log")
    else:

        handle_output(f"Total replacements made: {replacements_made}", "alllogs")
        _net_failed = max(0, replacements_failed - _replacements_resolved)
        handle_output(f"Total replacements failed: {_net_failed}", "alllogs")

        successful_mods = list(set(successful_mods))
        failed_mods = list(set(failed_mods))

        # Build Warned Mods: mods with conflicts or dup warnings but no real failures
        all_warned = warned_mods | dup_warned_mods
        warned_only = sorted(m for m in all_warned if m not in failed_mods)
        # Clean successful: remove mods that only appear due to conflicts
        clean_successful = sorted(m for m in successful_mods
                                  if m not in failed_mods and m not in all_warned)
        # Also include warned mods that had at least one success in successful list
        warned_with_success = sorted(m for m in all_warned
                                     if m in successful_mods and m not in failed_mods)

        handle_output("\nSuccessful Mods:", "alllogs")
        if clean_successful:
            for mod in clean_successful:
                handle_output(f"\t{mod}", "alllogs")
        else:
            handle_output("\tNone", "alllogs")

        handle_output("\nWarned Mods (conflicts/duplicates only):", "alllogs")
        if warned_only or warned_with_success:
            for mod in sorted(set(warned_only + warned_with_success)):
                handle_output(f"\t{mod}", "alllogs")
        else:
            handle_output("\tNone", "alllogs")

        handle_output("\nFailed Mods:", "alllogs")
        if failed_mods:
            for mod in sorted(failed_mods):
                handle_output(f"\t{mod}", "alllogs")
        else:
            handle_output("\tNone", "alllogs")

    # ---- v0.7.1: Dry-run mode -- skip writing output file ----
    if _dry_run:
        handle_output(
            f"DRY-RUN: {replacements_made} changes would be made, "
            f"{max(0, replacements_failed - _replacements_resolved)} would fail. "
            f"Output file NOT written.",
            "alllogs"
        )
        print(
            f"\n[DRY-RUN] {replacements_made} change(s) would be applied, "
            f"{max(0, replacements_failed - _replacements_resolved)} would fail.\n"
            f"Check {log_file} for details. No output file was written."
        )
    else:
        with open(patched_file, 'w', encoding='utf-8') as file:
            file.write(html_content)

    flush_logs()
    handle_output("Mod patching complete.", "log")
    return replacements_made, replacements_failed, failed_mods

#Function to Run the Main Logic
def _run_patch_cycle():
    """Single patch cycle -- load mods, patch HTML, write output. Called by main() and watch loop."""
    _t_start = time.perf_counter()

    # Setup folders
    create_directories()

    # Rich startup banner
    if _RICH_AVAILABLE:
        _console.rule("[bold blue]KittyPatcher v0.7.6[/bold blue]")
        engine_info = f"regex={_REGEX_ENGINE}  bs4_parser={KittyHTMLLayer('').bs4_parser if _RICH_AVAILABLE else '?'}"
        _console.print(f"[dim]{engine_info}[/dim]")
        if _dry_run:
            _console.print("[bold cyan]DRY-RUN mode -- no output file will be written[/bold cyan]")
        if _watch_mode:
            _console.print("[bold yellow]WATCH mode active -- re-patching on mod file changes[/bold yellow]")
    else:
        print("KittyPatcher v0.7.6")

    # ---- v0.7.3: Patch cache ----
    _cache_key  = ""
    _cache_hit  = False
    if _cache_enabled() and not _dry_run:
        _t_hash = time.perf_counter()
        _cache_key = _compute_cache_key(html_file, mods_folder)
        _t_hash_elapsed = time.perf_counter() - _t_hash
        _cached_path = _cache_lookup(_cache_key)
        if _cached_path:
            _cache_hit = True
            try:
                shutil.copy2(_cached_path, patched_file)
                _t_total = time.perf_counter() - _t_start
                cache_msg = (
                    f"Cache hit -- output copied from cache "
                    f"(hash: {_cache_key[:12]}..., "
                    f"hashed in {_t_hash_elapsed:.2f}s, "
                    f"total: {_t_total:.2f}s)"
                )
                handle_output(cache_msg, "alllogs")
                if _RICH_AVAILABLE:
                    _console.print(f"[green]{cache_msg}[/green]")
                    _console.rule()
                else:
                    print(cache_msg)
                return
            except Exception as _ce:
                handle_output(f"Cache copy failed ({_ce}), running full patch.", "log")
                _cache_hit = False

    _t_load = time.perf_counter()
    mod_dict, mod_list, mod_file_indexes, successful_mod_files, mod_reg_list, mod_struct_list, mod_func_list, mod_hook_list, conflict_map, passage_registry, passage_names_seen, js_registry, css_registry, events_registry, key_to_mod = load_mods(mods_folder)
    _t_load_done = time.perf_counter()

    _t_patch = time.perf_counter()
    _patch_made, _patch_failed, _patch_failed_mods = patch_html_file(
        html_file, mod_dict, mod_list, mod_file_indexes,
        mod_reg_list, mod_struct_list, mod_func_list, mod_hook_list,
        conflict_map, loaded_mod_files=successful_mod_files,
        passage_registry=passage_registry, passage_names_seen=passage_names_seen,
        js_registry=js_registry, css_registry=css_registry,
        events_registry=events_registry, key_to_mod=key_to_mod
    )
    _t_patch_done = time.perf_counter()

    # ---- v0.7.3: Store in cache ONLY when patch had zero hard failures ----
    if _cache_enabled() and not _dry_run and _cache_key and not _cache_hit:
        if _patch_failed == 0:
            try:
                if os.path.exists(patched_file):
                    with open(patched_file, "r", encoding="utf-8") as _cf:
                        _patched_content = _cf.read()
                    _cache_store(_cache_key, _patched_content, successful_mod_files)
                    _cache_prune(_cache_key)
            except Exception:
                pass
        else:
            handle_output(
                f"Cache: skipping store -- {_patch_failed} failure(s) in this patch run.",
                "log"
            )

    # Log summary
    for mod_file in mod_file_indexes:
        handle_output(f"{mod_file}", "alllogs")

    handle_output(
        f"Mod files processed: {', '.join(successful_mod_files)}\n",
        "log"
    )

    handle_output(
        f"Check the log file '{log_file}' for detailed patch information.",
        "log"
    )

    # Timing summary
    _t_total = time.perf_counter() - _t_start
    _t_load_elapsed = _t_load_done - _t_load
    _t_patch_elapsed = _t_patch_done - _t_patch
    timing_msg = f"Completed in {_t_total:.2f}s (load: {_t_load_elapsed:.2f}s, patch: {_t_patch_elapsed:.2f}s)"
    handle_output(timing_msg, "alllogs")

    if _RICH_AVAILABLE:
        _console.print(f"[green]{timing_msg}[/green]")
        _console.rule()
    else:
        handle_output("Mod patching complete.", "console")
        handle_output(
            f"Check the log file '{log_file}' for detailed information on what was replaced.",
            "console"
        )


def main():
    try:
        _run_patch_cycle()

        # Open game in browser (skip in watch mode -- reloading is manual)
        if running_from_cli() and not _watch_mode:
            open_in_browser(patched_file)

        # v0.7.1: watchdog watch loop
        if _watch_mode:
            if not _WATCHDOG_AVAILABLE:
                print("WARNING: watchdog not installed. Run: pip install watchdog")
                print("Falling back to 2-second poll watch mode.")
                _poll_watch_loop()
            else:
                _watchdog_watch_loop()
            return

    except Exception as e:
        if _RICH_AVAILABLE:
            _console.print_exception()
        else:
            handle_output(f"An error occurred: {e}", "console")
        sys.exit(1)

    finally:
        if running_from_cli() and not _watch_mode:
            input("Press Enter to exit...")


# ---- v0.7.1: Watch mode implementations ----

def _poll_watch_loop():
    """Fallback poll-based watch when watchdog is not installed."""
    print(f"Watching {mods_folder} for changes (polling every 2s). Ctrl+C to stop.")
    _mod_mtimes = {}

    def _snapshot():
        mtimes = {}
        for root, _, files in os.walk(mods_folder):
            for f in files:
                if any(f.endswith(ext) for ext in ('.mod', '.kdiff', '.patch')):
                    p = os.path.join(root, f)
                    try:
                        mtimes[p] = os.path.getmtime(p)
                    except OSError:
                        pass
        return mtimes

    _mod_mtimes.update(_snapshot())
    try:
        while True:
            time.sleep(2)
            current = _snapshot()
            if current != _mod_mtimes:
                changed = [p for p in current if current[p] != _mod_mtimes.get(p, 0)]
                changed += [p for p in _mod_mtimes if p not in current]
                print(f"\nMod change detected: {[os.path.basename(p) for p in changed]}")
                _mod_mtimes.update(current)
                try:
                    _run_patch_cycle()
                except Exception as e:
                    print(f"Patch error: {e}")
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")


def _watchdog_watch_loop():
    """Watchdog-based watch mode -- event-driven, no polling."""
    import threading

    if _RICH_AVAILABLE:
        _console.print(f"[bold yellow]Watching {mods_folder} for mod file changes. Ctrl+C to stop.[/bold yellow]")
    else:
        print(f"Watching {mods_folder} for mod file changes. Ctrl+C to stop.")

    _patch_lock = threading.Lock()
    _pending = threading.Event()

    class _ModHandler(_WatchdogHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            src = getattr(event, 'src_path', '')
            if any(src.endswith(ext) for ext in ('.mod', '.kdiff', '.patch')):
                _pending.set()

    observer = _WatchdogObserver()
    observer.schedule(_ModHandler(), mods_folder, recursive=True)
    observer.start()

    try:
        while True:
            _pending.wait()
            _pending.clear()
            time.sleep(0.3)  # debounce: coalesce rapid saves
            if _pending.is_set():
                continue
            with _patch_lock:
                if _RICH_AVAILABLE:
                    _console.print("[bold yellow]Change detected -- re-patching...[/bold yellow]")
                else:
                    print("Change detected -- re-patching...")
                try:
                    _run_patch_cycle()
                except Exception as e:
                    if _RICH_AVAILABLE:
                        _console.print_exception()
                    else:
                        print(f"Patch error: {e}")
    except KeyboardInterrupt:
        if _RICH_AVAILABLE:
            _console.print("[dim]Watch mode stopped.[/dim]")
        else:
            print("\nWatch mode stopped.")
    finally:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    main()
