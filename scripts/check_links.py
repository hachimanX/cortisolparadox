#!/usr/bin/env python3
"""Crawl every href in the built site and report internal targets that 404.

Also fails if a published page links to a guide slug that is not in
_articles/publish.json. Slugs in WATCH are reported one by one. A watched
slug that has since been added to publish.json is no longer forbidden.

Usage:
    python3 scripts/check_links.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE_HOSTS = {"cortisolparadox.com", "www.cortisolparadox.com"}
HREF = re.compile(r"""href\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
GUIDE_SLUG = re.compile(r"/guides/([a-z0-9-]+)(?:/|$|\?|#)")
DATA_GUIDE = re.compile(r"""data-guide\s*=\s*["']([a-z0-9-]+)["']""")

# Reported explicitly for this site. Once a slug is in publish.json it is
# allowed to be a real link, so this list does not have to be edited on publish.
WATCH = [
    "how-to-calm-your-nervous-system",
    "dysregulated-nervous-system",
    "waking-up-at-3am-cortisol",
    "coffee-and-cortisol",
    "cortisol-face",
    "cortisol-belly",
    "why-is-cortisol-high-in-the-morning",
    "magnesium-and-cortisol",
    "food-and-cortisol",
    "at-home-cortisol-test",
    "cortisol-supplements",
    "cortisol-and-blood-sugar",
    "high-cortisol-symptoms",
    "normal-cortisol-levels",
]


def published_slugs() -> set[str]:
    path = ROOT / "_articles" / "publish.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["slug"] for item in data}


def html_files() -> list[Path]:
    return sorted(ROOT.glob("*.html")) + sorted((ROOT / "guides").rglob("*.html"))


def locate(href: str, source: Path):
    """Return ('ok', file, fragment), ('external',), ('skip',), or ('missing', detail)."""
    raw = href.strip()
    if not raw or raw.startswith(("mailto:", "tel:", "javascript:")):
        return ("skip",)
    parts = urlparse(raw)
    fragment = unquote(parts.fragment)
    if parts.scheme in ("http", "https"):
        host = parts.netloc.lower().split(":")[0]
        if host not in SITE_HOSTS:
            return ("external",)
        path = unquote(parts.path)
        base = ROOT
        relative = path.lstrip("/")
    elif parts.scheme or parts.netloc:
        return ("skip",)
    else:
        path = unquote(parts.path)
        if path.startswith("/"):
            base = ROOT
            relative = path.lstrip("/")
        elif path == "":
            return ("ok", source, fragment)
        else:
            base = source.parent
            relative = path

    if relative in ("",):
        candidate = ROOT / "index.html"
    elif relative.endswith("/"):
        candidate = (base / relative / "index.html")
    else:
        candidate = base / relative
        if candidate.is_dir():
            candidate = candidate / "index.html"
    try:
        candidate = candidate.resolve()
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return ("missing", f"{href} escapes the site root")
    if not candidate.is_file():
        return ("missing", f"{source.relative_to(ROOT)} -> {href} ({candidate.relative_to(ROOT)})")
    return ("ok", candidate, fragment)


def has_fragment(path: Path, fragment: str, cache: dict[Path, str]) -> bool:
    if not fragment:
        return True
    text = cache.get(path)
    if text is None:
        text = path.read_text(encoding="utf-8")
        cache[path] = text
    pattern = re.compile(rf"""\s(?:id|name)\s*=\s*(['"]){re.escape(fragment)}\1""")
    return pattern.search(text) is not None


def sitemap_targets() -> list[str]:
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>(.*?)</loc>", text)


def main() -> None:
    published = published_slugs()
    files = html_files()
    cache: dict[Path, str] = {}
    missing: list[str] = []
    fragments: list[str] = []
    href_count = 0
    internal = 0
    external = 0
    guide_href_slugs: set[str] = set()
    placeholders: set[str] = set()
    unpublished_hrefs: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        cache[path] = text
        placeholders.update(DATA_GUIDE.findall(text))
        for match in HREF.finditer(text):
            href = match.group(1) if match.group(1) is not None else match.group(2)
            href_count += 1
            for slug in GUIDE_SLUG.findall(href):
                guide_href_slugs.add(slug)
                if slug not in published:
                    unpublished_hrefs.append(f"{path.relative_to(ROOT)} -> {href}")
            found = locate(href, path)
            if found[0] == "external":
                external += 1
                continue
            if found[0] == "skip":
                continue
            if found[0] == "missing":
                missing.append(found[1])
                continue
            internal += 1
            target, fragment = found[1], found[2]
            if fragment and not has_fragment(target, fragment, cache):
                fragments.append(f"{path.relative_to(ROOT)} -> {href} (no #{fragment} in {target.relative_to(ROOT)})")

    sitemap_missing = []
    for loc in sitemap_targets():
        found = locate(loc, ROOT / "sitemap.xml")
        if found[0] != "ok":
            sitemap_missing.append(loc)

    watched_hits: list[str] = []
    print(f"Pages: {len(files)}")
    print(f"Hrefs: {href_count}")
    print(f"Internal checked: {internal}")
    print(f"External skipped: {external}")
    print(f"Internal 404s: {len(missing)}")
    for item in missing:
        print(f"  MISSING {item}")
    print(f"Fragment misses: {len(fragments)}")
    for item in fragments:
        print(f"  FRAGMENT {item}")
    print(f"Sitemap URLs: {len(sitemap_targets())}")
    print(f"Sitemap targets missing: {len(sitemap_missing)}")
    for loc in sitemap_missing:
        print(f"  SITEMAP {loc}")
    print(f"Unpublished guide hrefs: {len(unpublished_hrefs)}")
    for item in unpublished_hrefs:
        print(f"  HREF {item}")
    print("Watched slugs:")
    for slug in WATCH:
        hits = 0
        for path in files:
            for match in HREF.finditer(cache[path]):
                href = match.group(1) if match.group(1) is not None else match.group(2)
                if GUIDE_SLUG.search(href) and GUIDE_SLUG.search(href).group(1) == slug:
                    hits += 1
        state = "published" if slug in published else "unpublished"
        print(f"  {slug}: {hits} hrefs ({state})")
        if hits and slug not in published:
            watched_hits.append(slug)
    print("data-guide placeholders: " + (", ".join(sorted(placeholders)) if placeholders else "(none)"))
    linked = ", ".join(sorted(guide_href_slugs)) if guide_href_slugs else "(none)"
    print(f"Guide href slugs: {linked}")

    failed = missing or fragments or sitemap_missing or unpublished_hrefs or watched_hits
    if failed:
        raise SystemExit(1)
    print("OK")


if __name__ == "__main__":
    main()
