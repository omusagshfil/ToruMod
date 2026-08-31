#!/usr/bin/env python3
"""
KittyToolingCommon v0.7.2
-------------------------
Shared helper library for KittyPatcher ecosystem tools.
Required by KittyPatcher, KittyValidate, KittyDiffAssist,
KittyModConverter, KittyPort, KittyToolbench, and KittyScaffold.

Original author : Kitty/LK
Maintained by   : CoderMaverick (with permission)
License         : Unauthorized redistribution without attribution is not permitted
"""

__author__  = "CoderMaverick"
__credits__ = ["Kitty/LK (original creator)"]
__version__ = "0.7.2"
__license__ = "Unauthorized redistribution without attribution is not permitted"


import importlib.util
import os
import re
import sys
import traceback
from pathlib import Path

# v0.7.1: use `regex` as drop-in replacement for stdlib `re` when available.
# Better backtracking safety on complex DOTALL patterns; possessive quantifiers.
# Falls back silently to stdlib re -- zero API change either way.
try:
    import regex as re  # noqa: F811  (intentional re-import)
    _REGEX_ENGINE = "regex"
except ImportError:
    _REGEX_ENGINE = "re"

try:
    import tomlkit
    _TOMLKIT_AVAILABLE = True
except ImportError:
    _TOMLKIT_AVAILABLE = False


# ---------------------------------------------------------------------------
# KittyConfig -- shared TOML configuration layer (v0.7.0)
# ---------------------------------------------------------------------------
# All tools use this class instead of rolling their own configparser calls.
# Config file: kitty_config.toml (replaces kitty_config.ini).
#
# On first use, if kitty_config.ini exists and no .toml exists, the INI is
# migrated automatically and the old file is renamed to kitty_config.ini.bak.
#
# Sections / keys:
#   [logging]
#     verbose = false
#
#   [browser]
#     name     = "Chrome"
#     path     = "C:/..."
#     chromium = true
#
#   [load_order]
#     # Mods listed here are loaded first in declared sequence.
#     # Remaining mods follow in alphabetical order.
#     order = ["CM_RO.v1.mod", "CM_BC.v1.mod"]
# ---------------------------------------------------------------------------

class KittyConfig:
    """
    Read/write wrapper around kitty_config.toml.

    Usage:
        cfg = KittyConfig(script_dir)
        verbose = cfg.get("logging", "verbose", False)
        cfg.set("browser", "name", "Firefox")
        cfg.save()
    """

    FILENAME = "kitty_config.toml"
    LEGACY_FILENAME = "kitty_config.ini"

    def __init__(self, directory: str):
        self._dir = directory
        self._path = os.path.join(directory, self.FILENAME)
        self._legacy_path = os.path.join(directory, self.LEGACY_FILENAME)
        self._doc = None
        self._load()

    # ---- internal -------------------------------------------------------

    def _empty_doc(self):
        if _TOMLKIT_AVAILABLE:
            doc = tomlkit.document()
            doc.add(tomlkit.comment("KittyPatcher configuration -- https://github.com/CoderMaverick"))
            doc.add(tomlkit.nl())
            return doc
        return {}

    def _load(self):
        if _TOMLKIT_AVAILABLE:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    self._doc = tomlkit.load(f)
            elif os.path.exists(self._legacy_path):
                self._doc = self._migrate_ini()
            else:
                self._doc = self._empty_doc()
        else:
            self._doc = self._load_fallback()

    def _migrate_ini(self):
        """
        Convert kitty_config.ini to TOML.  Called once when the .toml does not
        yet exist.  The old .ini is renamed to .ini.bak so it is not re-read.
        """
        import configparser
        cp = configparser.ConfigParser()
        cp.read(self._legacy_path, encoding="utf-8")

        if _TOMLKIT_AVAILABLE:
            doc = self._empty_doc()
            for section in cp.sections():
                t = tomlkit.table()
                for key, value in cp.items(section):
                    if value.lower() in ("true", "false"):
                        t.add(key, value.lower() == "true")
                    else:
                        t.add(key, value)
                doc.add(section, t)
        else:
            doc = {}
            for section in cp.sections():
                doc[section] = {}
                for key, value in cp.items(section):
                    if value.lower() in ("true", "false"):
                        doc[section][key] = value.lower() == "true"
                    else:
                        doc[section][key] = value

        # Persist the new TOML immediately
        self._doc = doc
        self.save()

        # Rename old INI so it is not picked up again
        bak = self._legacy_path + ".bak"
        try:
            os.rename(self._legacy_path, bak)
        except OSError:
            pass

        print(f"[KittyConfig] Migrated {self.LEGACY_FILENAME} -> {self.FILENAME} "
              f"(old file renamed to {os.path.basename(bak)})")
        return doc

    def _load_fallback(self):
        """Plain-dict fallback when tomlkit is not installed."""
        if not os.path.exists(self._path):
            return {}
        try:
            import json
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # ---- public API -----------------------------------------------------

    def get(self, section: str, key: str, default=None):
        """Return config[section][key] or default if not present."""
        try:
            val = self._doc[section][key]
            # tomlkit wraps booleans transparently; plain dict also works
            return val
        except (KeyError, TypeError):
            return default

    def set(self, section: str, key: str, value):
        """Write config[section][key] = value (does not auto-save)."""
        if _TOMLKIT_AVAILABLE:
            if section not in self._doc:
                self._doc.add(section, tomlkit.table())
            self._doc[section][key] = value
        else:
            if section not in self._doc:
                self._doc[section] = {}
            self._doc[section][key] = value

    def has_section(self, section: str) -> bool:
        return section in self._doc

    def save(self):
        """Write current state to kitty_config.toml."""
        if _TOMLKIT_AVAILABLE:
            with open(self._path, "w", encoding="utf-8") as f:
                tomlkit.dump(self._doc, f)
        else:
            import json
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._doc, f, indent=2)

    def get_load_order(self) -> list:
        """
        Return the explicit mod load order list from [load_order].order.
        Returns an empty list if the section or key is absent.
        The list contains bare mod filenames (e.g. "CM_RO.v1.mod").
        """
        raw = self.get("load_order", "order", [])
        if isinstance(raw, list):
            return [str(x) for x in raw]
        return []

    def set_load_order(self, order: list):
        """Persist a new mod load order list."""
        if _TOMLKIT_AVAILABLE:
            if "load_order" not in self._doc:
                self._doc.add("load_order", tomlkit.table())
            arr = tomlkit.array()
            for item in order:
                arr.append(item)
            self._doc["load_order"]["order"] = arr
        else:
            if "load_order" not in self._doc:
                self._doc["load_order"] = {}
            self._doc["load_order"]["order"] = list(order)

    @property
    def path(self) -> str:
        return self._path

    @property
    def exists(self) -> bool:
        return os.path.exists(self._path)


# ---------------------------------------------------------------------------
# Shared load-order resolver (v0.7.0)
# ---------------------------------------------------------------------------
# Used by load_mods (patcher), KittyValidate, KittyPort -- any tool that
# needs to walk a mods folder in consistent order.
# ---------------------------------------------------------------------------

VALID_MOD_EXTS = (".mod", ".kdiff", ".patch")


def _load_global_registry(mods_folder: str) -> dict:
    """
    Load the global dependency registry file from the mods folder, if present.

    The global registry is a single JSON file named 'cm_dependencies.json'
    placed anywhere in the mods folder (root or subfolder).  It maps mod
    stems (or bare filenames) to their dependency lists:

        {
          "CM_RO.v1":       ["?CM_FM.v1"],
          "CM_RORivals.v1": ["CM_RO.v1", "CM_FM.v1"]
        }

    Keys and dependency values are normalised through _stem() so extensions
    and casing don't matter.  Per-mod sidecar .json files (same base name as
    the .mod) take precedence over entries in this global file for that mod.

    Returns a dict mapping stem -> list-of-raw-dep-strings, or {} if not found.
    """
    import json
    registry_name = "cm_dependencies.json"
    for root, dirs, files in os.walk(mods_folder):
        dirs.sort()
        if registry_name in files:
            path = os.path.join(root, registry_name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if not isinstance(raw, dict):
                    print(f"WARNING: '{path}' must be a JSON object -- ignoring",
                          file=sys.stderr)
                    return {}
                # Normalise keys to stems
                return {_stem(k): v for k, v in raw.items()
                        if isinstance(v, list)}
            except Exception as e:
                print(f"WARNING: could not parse global registry '{path}': {e}",
                      file=sys.stderr)
    return {}


def _load_mod_sidecar(mod_path: str, global_registry: dict = None) -> dict:
    """
    Load dependency data for a mod file.

    Resolution order (highest priority first):
      1. Per-mod sidecar: <basename_no_ext>.json alongside the .mod file.
      2. Global registry: cm_dependencies.json in the mods folder
         (pre-loaded and passed in as global_registry).

    Per-mod sidecars always win -- they let individual mod authors override
    the global registry entry for their mod without touching the shared file.

    Returns a dict with at least a "dependencies" key, or {} if nothing found.

    Recognised fields:
      "dependencies": list of base filenames (no extension) that must load
                      before this mod.  Prefix "?" marks optional deps:
                      "?CM_RO.v1" means "load after CM_RO.v1 if present,
                      do not fail if absent".
    """
    import json
    base = os.path.splitext(mod_path)[0]  # strip .mod / .kdiff / .patch
    json_path = base + ".json"
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"WARNING: could not parse sidecar '{json_path}': {e}",
                  file=sys.stderr)
        # Per-mod file existed but failed to parse -- don't fall through
        # to global registry for this mod (avoids silent mis-ordering).
        return {}

    # No per-mod sidecar -- check global registry
    if global_registry:
        stem = _stem(os.path.basename(mod_path))
        if stem in global_registry:
            return {"dependencies": global_registry[stem]}

    return {}


def _stem(filename: str) -> str:
    """
    Return the dependency-resolution stem for a filename.

    Strips all recognised mod extensions so that "CM_RO.v1.mod",
    "CM_RO.v1.kdiff", and "CM_RO.v1" all normalise to "cm_ro.v1"
    (lowercase, no ext).  This lets sidecar dependencies written as
    "CM_RO.v1" match the actual file regardless of extension.
    """
    name = filename.lower()
    for ext in VALID_MOD_EXTS:
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    return name


def _topological_sort(keys: list, deps: dict, priorities: dict = None) -> tuple:
    """
    Kahn's algorithm topological sort with optional priority tiebreaking.

    keys       -- list of all node keys (lowercase stems)
    deps       -- dict: stem -> list of stems that must come BEFORE it
    priorities -- optional dict: stem -> int (lower = earlier, default 1000)
                  Used as tiebreaker when multiple nodes become ready together.
                  Does NOT override topological constraints -- only breaks ties
                  among nodes at the same topological level.

    Returns (sorted_list, cycle_members).
      sorted_list   -- keys in valid load order
      cycle_members -- set of keys involved in a cycle (empty if clean)
    """
    _priorities = priorities or {}
    DEFAULT_P   = 1000

    def _sort_key(stem: str):
        return (_priorities.get(stem, DEFAULT_P), stem)

    key_set = set(keys)

    predecessors = {k: set() for k in key_set}
    successors   = {k: []    for k in key_set}
    for node, preds in deps.items():
        if node not in key_set:
            continue
        for p in preds:
            if p not in key_set:
                continue
            predecessors[node].add(p)
            successors[p].append(node)

    # Sort ready queue by (priority, name) instead of name-only
    ready = sorted((k for k in key_set if not predecessors[k]), key=_sort_key)
    result = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        new_ready = []
        for successor in successors[node]:
            predecessors[successor].discard(node)
            if not predecessors[successor]:
                new_ready.append(successor)
        # Merge new_ready into ready maintaining priority sort
        ready = sorted(ready + new_ready, key=_sort_key)

    cycle_members = key_set - set(result)
    return result, cycle_members


def _merge_graph_with_config(graph_order: list, config_order: list) -> list:
    """
    Merge a topologically sorted graph_order with an explicit config_order.

    config_order entries win their relative positions.  All other mods
    from graph_order fill in between config anchors, preserving graph
    order among themselves.
    """
    if not config_order:
        return list(graph_order)

    config_set  = set(config_order)
    graph_pos   = {k: i for i, k in enumerate(graph_order)}
    config_rank = {k: i for i, k in enumerate(config_order)}

    pinned = sorted([k for k in graph_order if k in config_set],
                    key=lambda k: config_rank[k])
    free   = [k for k in graph_order if k not in config_set]

    result = []
    pi = fi = 0
    while pi < len(pinned) or fi < len(free):
        if pi >= len(pinned):
            result.append(free[fi]); fi += 1
        elif fi >= len(free):
            result.append(pinned[pi]); pi += 1
        elif graph_pos.get(pinned[pi], 0) <= graph_pos.get(free[fi], 0):
            result.append(pinned[pi]); pi += 1
        else:
            result.append(free[fi]); fi += 1

    return result


def resolve_mod_load_order(mods_folder: str, cfg: KittyConfig) -> list:
    """
    Return an ordered list of absolute mod file paths from mods_folder.

    Load order is determined by merging two inputs:

    1. Dependency graph  (partial order -- mods declare constraints)
       Two sources, per-mod sidecar wins over global registry:

       a) Global registry: cm_dependencies.json in the mods folder maps
          every mod stem to its dependency list.  Drop one file, done.
            {"CM_RO.v1": ["?CM_FM.v1"], "CM_RORivals.v1": ["CM_RO.v1", "CM_FM.v1"]}

       b) Per-mod sidecar: <basename>.json alongside the .mod file.
          Same format but scoped to one mod.  Overrides the global entry.
            {"dependencies": ["CM_RO.v1", "?CM_FM.v1"]}

       A leading "?" marks an optional dependency: load after if present,
       ignore silently if absent.  Hard dependencies that are missing from
       the folder produce a WARNING but do not abort the run.

    2. Priority: header in each mod file  (tiebreaker within a tier)
       Declare "# Priority: N" in the mod header (lower = earlier, default
       1000).  Only affects mods at the same topological level -- mods with
       no dependency relationship between them.  Does not override the graph.
       CM recommended: use this instead of editing kitty_config.toml for
       simple ordering preferences.

    3. [load_order] in kitty_config.toml  (explicit overrides -- always win)
       Mods listed here are placed in declared sequence.  Their positions
       override the graph-derived order for those specific mods.  All
       other mods fill in around them, preserving graph order.

    Conflict detection: if [load_order] specifies an order that violates a
    declared .json dependency, a WARNING is printed but the config order
    is still honoured (explicit override wins).

    Cycle detection: circular .json dependencies are detected and reported.
    Mods involved in a cycle are appended at the end alphabetically so the
    run can still proceed.
    """
    explicit = cfg.get_load_order()

    # Step 1: collect all mod files -- stem -> path
    all_files    = {}  # stem -> absolute path
    stem_to_fname = {}  # stem -> original basename (for messages)
    for root, dirs, files in os.walk(mods_folder):
        dirs.sort()
        files.sort()
        for fname in files:
            if any(fname.endswith(ext) for ext in VALID_MOD_EXTS):
                s = _stem(fname)
                if s not in all_files:
                    all_files[s]     = os.path.join(root, fname)
                    stem_to_fname[s] = fname

    all_stems = list(all_files.keys())

    # Step 2: load global registry + per-mod sidecars, build dependency graph
    # Global registry (cm_dependencies.json) provides a baseline for the whole
    # ecosystem.  Per-mod <basename>.json sidecars override it for that mod.
    # deps[stem] = list of stems that must load BEFORE stem
    global_registry = _load_global_registry(mods_folder)
    deps = {s: [] for s in all_stems}

    # Priority: header -- recommended CM mod field.
    # Read from each mod's header (first 50 lines max) as a tiebreaker
    # within the same topological tier. Mods with no declared dependency
    # relationship are sorted by (Priority, name) instead of name-only.
    # Does NOT override the dependency graph -- topology always wins.
    # Use cm_dependencies.json or sidecar .json for ordering constraints;
    # use Priority: only to nudge order within a tier without adding deps.
    # O(M * H) where H = avg header lines per mod (<< total file size).
    DEFAULT_PRIORITY = 1000
    priorities: dict = {}  # stem -> int priority
    for s, path in all_files.items():
        try:
            # Read only the header region (first 50 lines max) for speed
            with open(path, "r", encoding="utf-8", errors="ignore") as _fh:
                header_lines = []
                for _line in _fh:
                    stripped = _line.strip()
                    if stripped and not stripped.startswith('#') and stripped != '[Mod]':
                        break
                    header_lines.append(stripped)
                    if len(header_lines) >= 50:
                        break
            prio = DEFAULT_PRIORITY
            for _hl in header_lines:
                _pm = re.match(r'^#?\s*Priority\s*:\s*(\d+)', _hl, re.IGNORECASE)
                if _pm:
                    prio = int(_pm.group(1))
                    break
            priorities[s] = prio
        except OSError:
            priorities[s] = DEFAULT_PRIORITY
    for s, path in all_files.items():
        sidecar  = _load_mod_sidecar(path, global_registry=global_registry)
        raw_deps = sidecar.get("dependencies", [])
        if not isinstance(raw_deps, list):
            print(f"WARNING: '{stem_to_fname[s]}' sidecar 'dependencies' must be a list -- ignoring",
                  file=sys.stderr)
            continue
        for raw in raw_deps:
            raw      = str(raw)
            optional = raw.startswith("?")
            dep_raw  = raw.lstrip("?")
            dep_stem = _stem(dep_raw) if dep_raw else ""
            if not dep_stem:
                continue
            if dep_stem not in all_files:
                if not optional:
                    print(f"WARNING: '{stem_to_fname[s]}' declares dependency '{dep_raw}' "
                          f"which is not in the mods folder -- skipping dependency",
                          file=sys.stderr)
                continue
            deps[s].append(dep_stem)

    # Step 3: topological sort
    # Pass priorities into the sort so same-level nodes are ordered by
    # Priority: header value (lower = earlier) then alphabetically.
    graph_stems, cycle_members = _topological_sort(all_stems, deps,
                                                    priorities=priorities)
    if cycle_members:
        cycle_names = sorted(stem_to_fname.get(s, s) for s in cycle_members)
        print(f"WARNING: circular dependencies detected among: {cycle_names} "
              f"-- these mods will be appended in alphabetical order",
              file=sys.stderr)
        graph_stems.extend(sorted(cycle_members))

    # Step 4: resolve [load_order] config entries to stems
    config_stems = []
    for entry in explicit:
        s = _stem(entry)
        if s in all_files:
            config_stems.append(s)
        else:
            print(f"WARNING: [load_order] entry '{entry}' not found in mods folder -- skipping",
                  file=sys.stderr)

    # Step 5: conflict detection -- warn when config violates a declared dep
    config_rank = {s: i for i, s in enumerate(config_stems)}
    for s in config_stems:
        for pred in deps.get(s, []):
            if pred in config_rank and config_rank[pred] > config_rank[s]:
                print(
                    f"WARNING: [load_order] places '{stem_to_fname.get(s, s)}' before "
                    f"'{stem_to_fname.get(pred, pred)}', but '{stem_to_fname.get(s, s)}' "
                    f"declares a dependency on it -- config override honoured",
                    file=sys.stderr
                )

    # Step 6: merge graph order with config overrides
    final_stems = _merge_graph_with_config(graph_stems, config_stems)

    # Step 7: map stems back to absolute paths
    return [all_files[s] for s in final_stems if s in all_files]


# ---------------------------------------------------------------------------
# Compiled regex cache (v0.7.0) -- Phase 1.4
# ---------------------------------------------------------------------------
# All patcher regex operations go through _get_compiled() so patterns are
# compiled once per session rather than on every search call.
#
# Cache key is (pattern, flags) tuple so the same pattern string with
# different flags gets separate compiled objects.  Cache is capped at
# MAX_REGEX_CACHE entries with LRU eviction to prevent unbounded growth.
# ---------------------------------------------------------------------------

import functools

MAX_REGEX_CACHE = 4000  # v0.7.2: increased from 2000; 55-mod runs use ~300-600 unique patterns
_regex_cache: dict = {}
_regex_cache_order: list = []   # insertion-order LRU tracking


def _get_compiled(pattern: str, flags: int = 0):
    """
    Return a compiled re.Pattern for (pattern, flags), compiling and caching
    on first call.  LRU-evicts oldest entry when cache exceeds MAX_REGEX_CACHE.
    """
    key = (pattern, flags)
    if key in _regex_cache:
        return _regex_cache[key]
    compiled = re.compile(pattern, flags)
    _regex_cache[key] = compiled
    _regex_cache_order.append(key)
    if len(_regex_cache_order) > MAX_REGEX_CACHE:
        evict = _regex_cache_order.pop(0)
        _regex_cache.pop(evict, None)
    return compiled


def regex_cache_stats() -> dict:
    """Return current cache utilisation stats (for diagnostics/tests)."""
    return {"size": len(_regex_cache), "max": MAX_REGEX_CACHE}


# ---------------------------------------------------------------------------
# KittyHTMLLayer -- safe BeautifulSoup DOM wrapper (v0.7.0) -- Phase 2
# ---------------------------------------------------------------------------
# Encapsulates all BS4 operations so:
#   1. Passage body content is NEVER re-parsed by BS4 -- SugarCube macros
#      are opaque text as far as the DOM layer is concerned.
#   2. Structural operations (add/delete/rename passage, inject JS/CSS,
#      PID renormalization) use clean DOM calls instead of regex surgery.
#   3. Both patchers and KittyValidate share identical parse settings.
#
# This replaces the <e> tag workaround entirely.  The <e> tag existed to
# mark passage body boundaries so escape_twine_tags() knew what to encode.
# KittyHTMLLayer extracts body content via .decode_contents() -- a BS4
# method that returns the raw inner HTML string without touching it --
# and re-inserts via NavigableString after tag.clear().  BS4 never sees
# the SugarCube markup inside passage bodies.
#
# Usage:
#     layer = KittyHTMLLayer(html_string)
#     body  = layer.get_passage_body("EncounterWidgets")  # decoded raw string
#     layer.set_passage_body("EncounterWidgets", modified_body)
#     layer.add_passage(name, body, tags="", pid="auto")
#     layer.delete_passage("OldPassage")
#     layer.rename_passage("OldName", "NewName")
#     layer.append_js(js_code)
#     layer.append_css(css_code)
#     layer.append_events(events_code, anchor="setup.Events.db =\n[")
#     layer.set_passage_tags("PassageName", "tag1 tag2")
#     layer.add_passage_tag("PassageName", "newtag")
#     layer.remove_passage_tag("PassageName", "oldtag")
#     layer.renormalize_pids()
#     html_out = layer.serialize()
#
# When BS4 is not available the layer falls back to the existing raw-string
# operations so the patcher degrades gracefully without crashing.
# ---------------------------------------------------------------------------

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    _BS4_AVAILABLE = True
    # v0.7.1: prefer lxml parser (C-backed, 5-20x faster than html.parser).
    # Fall back to html.parser if lxml is not installed.
    try:
        import lxml  # noqa: F401
        _BS4_PARSER = "lxml"
    except ImportError:
        _BS4_PARSER = "html.parser"
except ImportError:
    _BS4_AVAILABLE = False
    _BS4_PARSER = "html.parser"


class KittyHTMLLayer:
    """
    Safe DOM wrapper around a COT HTML file.

    Passage body content is always treated as opaque raw text -- BS4 never
    re-parses the SugarCube markup inside <tw-passagedata> elements.
    This is the replacement for the <e> tag workaround.
    """

    def __init__(self, html_string: str):
        self._raw = html_string   # always kept in sync for fallback path
        self._soup = None
        self._passage_index: dict = {}   # name -> Tag (O(1) lookup)
        self._available = _BS4_AVAILABLE

        if self._available:
            self._soup = BeautifulSoup(html_string, _BS4_PARSER)
            self._build_index()

    # ---- index management -----------------------------------------------

    def _build_index(self):
        """Build name -> Tag dict from all <tw-passagedata> elements."""
        self._passage_index = {}
        for tag in self._soup.find_all("tw-passagedata"):
            name = tag.get("name")
            if name:
                if name in self._passage_index:
                    # Duplicate -- keep first occurrence, log as warning
                    import sys as _sys
                    print(f"WARNING: duplicate passage name in HTML index: '{name}'",
                          file=_sys.stderr)
                else:
                    self._passage_index[name] = tag

    def _update_index_rename(self, old_name: str, new_name: str):
        """Atomically update index after a rename operation."""
        tag = self._passage_index.pop(old_name, None)
        if tag is not None:
            self._passage_index[new_name] = tag

    def _remove_from_index(self, name: str):
        self._passage_index.pop(name, None)

    # ---- passage body access (THE KEY SAFE PATTERN) ---------------------

    @staticmethod
    def _extract_body(tag: "Tag") -> str:
        """
        Extract passage body in HTML-escaped form.

        Uses decode_contents() which returns the inner HTML as a string.
        For COT passages the body is HTML-escaped SugarCube content
        (<<if $x>> is stored as &lt;&lt;if $x&gt;&gt;).  decode_contents()
        returns that escaped form directly -- the same string the patcher
        already works with throughout its directive pipeline.

        Contract: body strings in KittyHTMLLayer are always HTML-escaped.
        get_passage_body() returns escaped form.
        set_passage_body() expects escaped form.
        """
        return tag.decode_contents()

    @staticmethod
    def _set_body(tag: "Tag", text: str):
        """
        Replace passage body with HTML-escaped text.

        text must be HTML-escaped (e.g. &lt;&lt;if $x&gt;&gt;) -- the same
        form the patcher works with throughout its directive pipeline.

        BS4 stores text nodes decoded internally (<<if $x>>).
        decode_contents() re-encodes them to &lt;&lt; on output.
        So we html.unescape() the input before inserting into NavigableString,
        and BS4 round-trips it back to the escaped form correctly.

        Passing already-escaped text directly to NavigableString would
        double-encode: &lt; -> &amp;lt; which breaks passage content.
        """
        import html as _html
        tag.clear()
        tag.append(NavigableString(_html.unescape(text)))

    # ---- public passage operations --------------------------------------

    def passage_exists(self, name: str) -> bool:
        if self._available:
            return name in self._passage_index
        return bool(re.search(
            r'<tw-passagedata[^>]*name="' + re.escape(name) + r'"', self._raw
        ))

    def get_passage_body(self, name: str) -> str | None:
        """Return decoded body string for named passage, or None if not found."""
        if not self._available:
            return self._fallback_get_body(name)
        tag = self._passage_index.get(name)
        if tag is None:
            return None
        return self._extract_body(tag)

    def set_passage_body(self, name: str, text: str) -> bool:
        """Replace body of named passage. Returns True on success."""
        if not self._available:
            return self._fallback_set_body(name, text)
        tag = self._passage_index.get(name)
        if tag is None:
            return False
        self._set_body(tag, text)
        return True

    def get_passage_tags_attr(self, name: str) -> str | None:
        """Return the tags= attribute string for named passage."""
        if not self._available:
            m = re.search(
                r'<tw-passagedata[^>]*name="' + re.escape(name) + r'"[^>]*tags="([^"]*)"',
                self._raw
            )
            return m.group(1) if m else None
        tag = self._passage_index.get(name)
        return tag.get("tags", "") if tag else None

    def set_passage_tags_attr(self, name: str, tags_str: str) -> bool:
        if not self._available:
            return False   # fallback: caller uses raw string ops
        tag = self._passage_index.get(name)
        if tag is None:
            return False
        tag["tags"] = tags_str
        return True

    def add_passage_tag(self, name: str, new_tag: str) -> bool:
        current = self.get_passage_tags_attr(name)
        if current is None:
            return False
        tags = [t for t in current.split() if t]
        if new_tag not in tags:
            tags.append(new_tag)
        return self.set_passage_tags_attr(name, " ".join(tags))

    def remove_passage_tag(self, name: str, old_tag: str) -> bool:
        current = self.get_passage_tags_attr(name)
        if current is None:
            return False
        tags = [t for t in current.split() if t and t != old_tag]
        return self.set_passage_tags_attr(name, " ".join(tags))

    def add_passage(self, name: str, body: str, tags: str = "",
                    pid: str = "auto", position: str = "100,100",
                    size: str = "100,100") -> bool:
        """
        Insert a new <tw-passagedata> element before </tw-storydata>.
        Body is treated as raw text -- not re-parsed.
        Returns False if BS4 unavailable or storydata not found.
        """
        if not self._available:
            return False
        storydata = self._soup.find("tw-storydata")
        if storydata is None:
            return False
        new_tag = self._soup.new_tag(
            "tw-passagedata",
            attrs={"pid": pid, "name": name, "tags": tags,
                   "position": position, "size": size}
        )
        self._set_body(new_tag, body)
        storydata.append(new_tag)
        self._passage_index[name] = new_tag
        return True

    def delete_passage(self, name: str) -> bool:
        """Remove a <tw-passagedata> element from the DOM entirely."""
        if not self._available:
            return False
        tag = self._passage_index.get(name)
        if tag is None:
            return False
        tag.decompose()
        self._remove_from_index(name)
        return True

    def rename_passage(self, old_name: str, new_name: str) -> bool:
        """Rename a passage in the DOM. Index updated atomically."""
        if not self._available:
            return False
        tag = self._passage_index.get(old_name)
        if tag is None:
            return False
        tag["name"] = new_name
        self._update_index_rename(old_name, new_name)
        return True

    def all_passage_names(self) -> list:
        if self._available:
            return list(self._passage_index.keys())
        return [m.group(1) for m in re.finditer(
            r'<tw-passagedata[^>]*name="([^"]+)"', self._raw
        )]

    # ---- JS / CSS / Events injection ------------------------------------

    def append_js(self, js_code: str) -> bool:
        """
        Append js_code to the last <script> block before <tw-passagedata>.
        Uses the same anchor as the current patcher (</script><tw-passagedata).
        """
        if not self._available:
            return False
        # Find the last script tag that is a sibling/ancestor of tw-storydata
        scripts = self._soup.find_all("script")
        if not scripts:
            return False
        target = scripts[-1]
        existing = target.string or ""
        target.string = existing + "\n" + js_code
        return True

    def append_css(self, css_code: str) -> bool:
        """Append css_code to the main <style> block."""
        if not self._available:
            return False
        style = self._soup.find("style")
        if style is None:
            return False
        existing = style.string or ""
        style.string = existing + "\n" + css_code
        return True

    def append_events(self, events_code: str, anchor: str = "setup.Events.db =\n[") -> bool:
        """
        Insert events_code after the Events.db array opening bracket.
        Falls back to raw string op since this is inside a script block --
        BS4 does not parse JS content.
        """
        # Events injection is always inside a script tag body -- raw string
        # operation is correct here and identical to what the patcher does.
        return False   # signals caller to use existing raw-string path

    # ---- PID renormalization --------------------------------------------

    def renormalize_pids(self) -> int:
        """
        Renumber all <tw-passagedata pid="..."> sequentially (1, 2, 3...)
        in document order.  Updates tw-storydata startnode to match.
        Returns total passage count.
        """
        if not self._available:
            return 0
        storydata = self._soup.find("tw-storydata")
        old_startnode = storydata.get("startnode") if storydata else None

        pid_map = {}
        counter = 0
        for tag in self._soup.find_all("tw-passagedata"):
            old_pid = str(tag.get("pid", "0"))
            counter += 1
            new_pid = str(counter)
            pid_map[old_pid] = new_pid
            tag["pid"] = new_pid

        if old_startnode and old_startnode in pid_map and storydata:
            storydata["startnode"] = pid_map[old_startnode]

        return counter

    # ---- storydata metadata ---------------------------------------------

    def get_storydata_attrs(self) -> dict:
        """Return tw-storydata attribute dict for diagnostic logging."""
        if not self._available:
            return {}
        sd = self._soup.find("tw-storydata")
        if sd is None:
            return {}
        return {k: v for k, v in sd.attrs.items()}

    def set_watermark(self, version: str):
        """Write data-kittypatcher=version to tw-storydata."""
        if not self._available:
            return
        sd = self._soup.find("tw-storydata")
        if sd is not None:
            sd["data-kittypatcher"] = version

    def get_watermark(self) -> str | None:
        """Return existing data-kittypatcher value, or None."""
        if not self._available:
            return None
        sd = self._soup.find("tw-storydata")
        if sd is None:
            return None
        return sd.get("data-kittypatcher")

    # ---- serialization --------------------------------------------------

    def serialize(self) -> str:
        """
        Return the final HTML string.

        Uses formatter="minimal" to avoid unnecessary entity expansion and
        preserve the passage content encoding that COT expects.
        """
        if not self._available:
            return self._raw
        return str(self._soup)

    def sync_raw(self):
        """
        Sync self._raw from the current soup state.
        Call this before any operation that still uses self._raw as fallback.
        """
        if self._available:
            self._raw = self.serialize()

    # ---- raw string fallbacks (BS4 not available) -----------------------

    def _fallback_get_body(self, name: str) -> str | None:
        m = re.search(
            r'<tw-passagedata[^>]*name="' + re.escape(name) + r'"[^>]*>(.*?)</tw-passagedata>',
            self._raw, re.DOTALL
        )
        if not m:
            return None
        return m.group(1)

    def _fallback_set_body(self, name: str, text: str) -> bool:
        import html as _html
        pat = re.compile(
            r'(<tw-passagedata[^>]*name="' + re.escape(name) + r'"[^>]*>)(.*?)(</tw-passagedata>)',
            re.DOTALL
        )
        new, n = pat.subn(lambda m: m.group(1) + text + m.group(3), self._raw, count=1)
        if n:
            self._raw = new
            return True
        return False

    # ---- availability check ---------------------------------------------

    @property
    def bs4_available(self) -> bool:
        return self._available

    @property
    def bs4_parser(self) -> str:
        """Return the BS4 parser name actually in use."""
        return _BS4_PARSER if self._available else "none"

    @property
    def regex_engine(self) -> str:
        """Return which regex engine is in use: 'regex' or 're'."""
        return _REGEX_ENGINE


# ---------------------------------------------------------------------------
# Module loader helpers (unchanged from v0.6.0)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# load_mod_source -- encoded mod transparent loader (v0.7.0)
# ---------------------------------------------------------------------------
# All tools that need to read mod content call this instead of open(mod_path).
# If the file is a plain .mod, it returns the raw text unchanged.
# If the file is KittyEncode encrypted, it decrypts in memory and returns the
# plaintext source string -- nothing is ever written to disk.
#
# Password resolution order:
#   1. explicit `password` argument
#   2. KITTY_KEY environment variable
#   3. key embedded in the stub (encode_file_embedded / --embed-key)
#   4. interactive getpass prompt (last resort)
# ---------------------------------------------------------------------------

def load_mod_source(mod_path, password=None, dist_secret=None):
    """
    Load mod source from a plain .mod file or any KittyEncode encrypted file.

    Three modes handled transparently:
      1. Plain .mod            -- returned as-is
      2. Embedded-key encoded  -- key extracted from stub, decrypted in memory
      3. Patcher-keyed encoded -- key derived from dist_secret + filename,
                                  decrypted in memory; no key in file at all

    For modes 2 and 3, decryption is entirely in memory.
    Nothing is written to disk. Plaintext exists only in the returned string.

    Args:
        mod_path:    path to the .mod or KittyEncode file
        password:    optional explicit password (str) -- for embedded-key mode
        dist_secret: bytes, _KITTY_DIST_SECRET from patcher -- for patcher-keyed mode

    Returns:
        str: the raw mod source text
    """
    import importlib.util as _ilu
    import getpass as _gp

    # Lazy-import kitty_encode from the same directory as this file
    _here = os.path.dirname(os.path.abspath(__file__))
    _ke_path = os.path.join(_here, 'kitty_encode.py')

    if not os.path.isfile(_ke_path):
        with open(mod_path, 'r', encoding='utf-8') as _f:
            return _f.read()

    _spec = _ilu.spec_from_file_location('kitty_encode', _ke_path)
    _ke = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_ke)

    if not _ke.is_encoded(mod_path):
        with open(mod_path, 'r', encoding='utf-8') as _f:
            return _f.read()

    # Patcher-keyed: no key in file, derive from dist_secret
    if _ke.is_patcher_keyed(mod_path):
        if dist_secret is None:
            raise RuntimeError(
                'Mod %s is patcher-keyed but no dist_secret was supplied to load_mod_source.'
                % os.path.basename(mod_path)
            )
        return _ke.decode_to_string_patcher_keyed(mod_path, dist_secret)

    # Embedded-key: extract from stub, silent for end users
    pw = (password
          or os.environ.get('KITTY_KEY')
          or _ke.extract_embedded_key(mod_path))

    if not pw:
        pw = _gp.getpass('[kitty] Password for %s: ' % os.path.basename(mod_path))

    return _ke.decode_to_string(mod_path, pw)


def latest_general_patcher_path(here, caller_name):
    """
    Find the highest-version KittyPatcher file next to caller.

    Prefers the unified KittyPatcher_v<ver>.py over legacy
    KittyPatcher_v<ver>.General.py when both exist at the same version.
    Excludes Modder-edition files.
    """
    candidates = [p for p in Path(here).glob('KittyPatcher_v*.py')
                  if not p.name.endswith('_Modder.py')
                  and not p.name.endswith('.Modder.py')]
    if not candidates:
        raise RuntimeError('No KittyPatcher_v*.py file found next to %s' % caller_name)

    def _version_key(path_obj):
        m = re.search(r'KittyPatcher_v(\d[\d_]+)', path_obj.name)
        if not m:
            return tuple()
        nums = tuple(int(x) for x in re.findall(r'\d+', m.group(1)))
        # Prefer shorter filename at same version (unified > _General > others)
        return (nums, -len(path_obj.name))

    best = max(candidates, key=_version_key)
    return str(best)
def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load module spec from %s' % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_latest_patcher_module(here, caller_name, module_name='kitty_patcher_general'):
    path = latest_general_patcher_path(here, caller_name)
    return load_module(path, module_name)


def print_error(exc, debug=False):
    if debug:
        traceback.print_exc()
    else:
        print('ERROR: %s' % exc, file=sys.stderr)


def is_interactive_cli():
    return sys.stdin.isatty()
