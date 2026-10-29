#!/usr/bin/env python3
"""Build /guides/ pages from markdown in _articles/.

Stdlib only. A link to /guides/<slug>/ is a real href only when that slug is
listed in _articles/publish.json and its source file is present. Every other
guide link is written as <span data-guide="slug">...</span> with no href.

Usage:
    python3 scripts/build_guides.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "_articles"
PUBLISH_FILE = ARTICLES_DIR / "publish.json"
GUIDES_DIR = ROOT / "guides"
SITEMAP = ROOT / "sitemap.xml"
SITE = "https://cortisolparadox.com"

GUIDE_HREF = re.compile(
    r"(?:https://cortisolparadox\.com)?/guides/([a-z0-9-]+)/?"
)
META_TITLE = re.compile(r"<!--\s*Meta title:\s*(.*?)\s*-->", re.DOTALL)
META_DESC = re.compile(r"<!--\s*Meta description:\s*(.*?)\s*-->", re.DOTALL)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)|\*\*(.+?)\*\*|\*(.+?)\*")
SLUG_NAME = re.compile(r"[a-z0-9-]+")
SEPARATOR_CELL = re.compile(r":?-{3,}:?")

HEADER_LOGO = """<svg width="188" height="38" viewBox="0 0 188 38" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect width="36" height="36" rx="8" fill="#0A192F"/>
          <path d="M12 18C12 14.6863 14.6863 12 18 12C21.3137 12 24 14.6863 24 18C24 21.3137 21.3137 24 18 24C14.6863 24 12 21.3137 12 18Z" stroke="#0D9488" stroke-width="2"/>
          <path d="M18 7V12M18 24V29M7 18H12M24 18H29" stroke="#0284C7" stroke-width="2" stroke-linecap="round"/>
          <circle cx="18" cy="18" r="2.5" fill="#F59E0B"/>
          <text x="46" y="25" font-family="Plus Jakarta Sans, sans-serif" font-weight="700" font-size="15" fill="#0A192F">Kinder Days Press</text>
        </svg>"""

FOOTER_LOGO = """<svg width="188" height="38" viewBox="0 0 188 38" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect width="36" height="36" rx="8" fill="#1E293B"/>
          <path d="M12 18C12 14.6863 14.6863 12 18 12C21.3137 12 24 14.6863 24 18C24 21.3137 21.3137 24 18 24C14.6863 24 12 21.3137 12 18Z" stroke="#14B8A6" stroke-width="2"/>
          <path d="M18 7V12M18 24V29M7 18H12M24 18H29" stroke="#38BDF8" stroke-width="2" stroke-linecap="round"/>
          <circle cx="18" cy="18" r="2.5" fill="#F59E0B"/>
          <text x="46" y="25" font-family="Plus Jakarta Sans, sans-serif" font-weight="700" font-size="15" fill="#FFFFFF">Kinder Days Press</text>
        </svg>"""


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slug_from_filename(path: Path) -> str:
    stem = re.sub(r"^\d+-", "", path.stem)
    if not SLUG_NAME.fullmatch(stem):
        die(f"{path.name}: slug {stem!r} must be lowercase letters, numbers, and hyphens")
    return stem


def render_inline(text: str, published: set[str]) -> str:
    parts: list[str] = []
    pos = 0
    for match in INLINE.finditer(text):
        parts.append(esc(text[pos:match.start()]))
        label, url, bold, italic = match.group(1), match.group(2), match.group(3), match.group(4)
        if label is not None:
            parts.append(render_link(label, url.strip(), published))
        elif bold is not None:
            parts.append("<strong>" + render_inline(bold, published) + "</strong>")
        else:
            parts.append("<em>" + render_inline(italic, published) + "</em>")
        pos = match.end()
    parts.append(esc(text[pos:]))
    return "".join(parts)


def render_link(label: str, url: str, published: set[str]) -> str:
    inner = render_inline(label, published)
    guide = GUIDE_HREF.fullmatch(url)
    if guide:
        slug = guide.group(1)
        if slug in published:
            return f'<a href="/guides/{slug}/">{inner}</a>'
        return f'<span data-guide="{slug}">{inner}</span>'
    return f'<a href="{esc(url)}">{inner}</a>'


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(SEPARATOR_CELL.fullmatch(cell) for cell in cells)


def render_table(lines: list[str], published: set[str]) -> str:
    rows = [split_row(line) for line in lines if not is_separator(line)]
    if not rows:
        die("empty table")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        die("table row has a different number of cells")
    head = rows[0]
    body = rows[1:]
    head_html = "".join(
        f"<th scope=\"col\">{render_inline(cell, published)}</th>" for cell in head
    )
    body_html = []
    for row in body:
        cells = "".join(f"<td>{render_inline(cell, published)}</td>" for cell in row)
        body_html.append(f"<tr>{cells}</tr>")
    return (
        '<div class="table-scroll"><table><thead><tr>'
        + head_html
        + "</tr></thead><tbody>"
        + "".join(body_html)
        + "</tbody></table></div>"
    )


def render_markdown(body: str, published: set[str]) -> str:
    lines = body.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            blocks.append(
                f"<h{level}>{render_inline(heading.group(2).strip(), published)}</h{level}>"
            )
            i += 1
            continue
        if line.lstrip().startswith("|"):
            table: list[str] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table.append(lines[i])
                i += 1
            blocks.append(render_table(table, published))
            continue
        if line.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{render_inline(lines[i][2:].strip(), published)}</li>")
                i += 1
            blocks.append("<ul>" + "".join(items) + "</ul>")
            continue
        blocks.append(f"<p>{render_inline(line.strip(), published)}</p>")
        i += 1
    return "\n".join(blocks)


def markdown_plain(body: str) -> str:
    text = COMMENT.sub("", body).replace("\r\n", "\n")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    kept: list[str] = []
    for line in text.split("\n"):
        if is_separator(line) and "|" in line:
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^-\s+", "", line)
        line = line.replace("|", " ")
        kept.append(line)
    text = "\n".join(kept)
    text = text.replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "tr", "div"}:
            self.parts.append(" ")


def html_plain(fragment: str) -> str:
    parser = _Text()
    parser.feed(fragment)
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def assert_copy_preserved(source: Path, body: str, html: str) -> None:
    expected = markdown_plain(body)
    actual = html_plain(html)
    if expected != actual:
        die(
            f"{source.name}: rendered text does not match the markdown.\n"
            f"--- markdown ---\n{expected[:500]}\n--- html ---\n{actual[:500]}"
        )


def load_publish() -> list[dict]:
    if not PUBLISH_FILE.is_file():
        die(f"missing {PUBLISH_FILE.relative_to(ROOT)}")
    try:
        data = json.loads(PUBLISH_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"publish.json: {exc}")
    if not isinstance(data, list):
        die("publish.json must be a list of {slug, date} objects")
    entries = []
    seen: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict) or "slug" not in item or "date" not in item:
            die(f"publish.json entry {index} needs slug and date")
        slug = item["slug"]
        raw_date = item["date"]
        if not isinstance(slug, str) or not SLUG_NAME.fullmatch(slug):
            die(f"publish.json: bad slug {slug!r}")
        if slug in seen:
            die(f"publish.json: duplicate slug {slug}")
        seen.add(slug)
        try:
            published_on = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            die(f"publish.json: {slug} has bad date {raw_date!r}")
        if raw_date != published_on.isoformat():
            die(f"publish.json: {slug} date must be YYYY-MM-DD")
        entries.append({"slug": slug, "date": published_on, "order": index})
    return entries


def load_sources(entries: list[dict]) -> list[dict]:
    files = sorted(ARTICLES_DIR.glob("*.md"))
    by_slug: dict[str, Path] = {}
    for path in files:
        slug = slug_from_filename(path)
        if slug in by_slug:
            die(f"{path.name} and {by_slug[slug].name} both use slug {slug}")
        by_slug[slug] = path
    published = {entry["slug"] for entry in entries}
    articles = []
    for entry in entries:
        path = by_slug.get(entry["slug"])
        if path is None:
            die(f"no markdown file for published slug {entry['slug']}")
        raw = path.read_text(encoding="utf-8")
        title_match = META_TITLE.search(raw)
        desc_match = META_DESC.search(raw)
        if not title_match or not desc_match:
            die(f"{path.name}: missing Meta title or Meta description comment")
        body = COMMENT.sub("", raw).strip()
        if not body.startswith("# "):
            die(f"{path.name}: article must start with one # heading after the comments")
        headline = body.split("\n", 1)[0][2:].strip()
        articles.append(
            {
                **entry,
                "path": path,
                "meta_title": title_match.group(1).strip(),
                "meta_description": desc_match.group(1).strip(),
                "headline": headline,
                "body": body,
            }
        )
    for slug, path in by_slug.items():
        if slug not in published:
            print(f"skip unpublished source: {path.relative_to(ROOT)}")
    articles.sort(key=lambda article: (article["date"], article["order"]), reverse=True)
    return articles


def json_ld(article: dict, canonical: str) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["headline"],
        "datePublished": article["date"].isoformat(),
        "mainEntityOfPage": canonical,
        "publisher": {"@type": "Organization", "name": "Kinder Days Press"},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")


def page(*, title: str, description: str, canonical: str, og_type: str, main: str, json_ld_text: str | None, nav_href: str, nav_label: str) -> str:
    structured = ""
    if json_ld_text:
        structured = f'\n  <script type="application/ld+json">\n{json_ld_text}\n  </script>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="/assets/guides.css">{structured}
</head>
<body class="article-page">
  <header class="site-nav">
    <div class="container nav-wrapper">
      <a href="/" class="brand-logo-link" aria-label="Kinder Days Press home">
        {HEADER_LOGO}
      </a>
      <a href="{esc(nav_href)}" class="nav-text-link">{esc(nav_label)}</a>
    </div>
  </header>
  <main class="legal-main">
    <div class="container legal-wrap article-wrap">
{main}
    </div>
  </main>
  <footer class="site-footer">
    <div class="container footer-inner">
      <div class="footer-logo">
        {FOOTER_LOGO}
      </div>
      <ul class="footer-links">
        <li><a href="/">Guide</a></li>
        <li><a href="/guides/">Guides</a></li>
        <li><a href="/privacy.html">Privacy</a></li>
        <li><a href="/terms.html">Terms</a></li>
        <li><a href="/refund.html">Refunds</a></li>
      </ul>
      <p class="footer-contact">To reach us, email <a href="mailto:support@cortisolparadox.com">support@cortisolparadox.com</a>, or reply to your Payhip purchase receipt email.</p>
      <p class="footer-publisher">Publisher: Kinder Days Press</p>
      <div class="footer-disclaimer-box">
        <p class="footer-disclaimer-text">Educational content only. This website and the downloadable files are not medical advice, not a diagnosis, and not a treatment. Talk to your doctor before you change how you eat, how you move, or how you sleep, especially if you have a health condition or take medication.</p>
      </div>
      <p class="footer-copyright">Copyright © 2026 Kinder Days Press. All rights reserved.</p>
    </div>
  </footer>
</body>
</html>
"""


def write_article(article: dict, published: set[str]) -> None:
    html_body = render_markdown(article["body"], published)
    assert_copy_preserved(article["path"], article["body"], html_body)
    if "Commodity test" in html_body or "Meta title:" in html_body:
        die(f"{article['path'].name}: source comments leaked into the page")
    canonical = f"{SITE}/guides/{article['slug']}/"
    main = f'      <p class="article-kicker"><a href="/guides/">Guides</a></p>\n      <article class="article-body">\n{html_body}\n      </article>'
    document = page(
        title=article["meta_title"],
        description=article["meta_description"],
        canonical=canonical,
        og_type="article",
        main=main,
        json_ld_text=json_ld(article, canonical),
        nav_href="/guides/",
        nav_label="Guides",
    )
    target = GUIDES_DIR / article["slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")


def write_index(articles: list[dict]) -> None:
    items = []
    for article in articles:
        items.append(
            "        <li>\n"
            f'          <h2><a href="/guides/{article["slug"]}/">{esc(article["meta_title"])}</a></h2>\n'
            f'          <p>{esc(article["meta_description"])}</p>\n'
            "        </li>"
        )
    listing = "\n".join(items) if items else '        <li><p>No guides published yet.</p></li>'
    main = (
        '      <h1 class="legal-title">Guides</h1>\n'
        "      <p>Research notes on cortisol, sleep, and the nervous system.</p>\n"
        '      <ul class="guide-index">\n'
        f"{listing}\n"
        "      </ul>"
    )
    latest = max(article["date"] for article in articles).isoformat() if articles else date.today().isoformat()
    document = page(
        title="Guides — The Cortisol Paradox",
        description="Research notes on cortisol, sleep, and the nervous system from Kinder Days Press.",
        canonical=f"{SITE}/guides/",
        og_type="website",
        main=main,
        json_ld_text=None,
        nav_href="/",
        nav_label="Back to the guide",
    )
    (GUIDES_DIR / "index.html").write_text(document, encoding="utf-8")
    return latest


def update_sitemap(articles: list[dict], index_lastmod: str) -> None:
    if not SITEMAP.is_file():
        die("sitemap.xml is missing")
    text = SITEMAP.read_text(encoding="utf-8")
    text = re.sub(
        r"\n  <url>\n    <loc>https://cortisolparadox\.com/guides/[^<]*</loc>\n    <lastmod>[^<]*</lastmod>\n  </url>",
        "",
        text,
    )
    blocks = [
        "  <url>\n"
        f"    <loc>{SITE}/guides/</loc>\n"
        f"    <lastmod>{index_lastmod}</lastmod>\n"
        "  </url>"
    ]
    for article in articles:
        blocks.append(
            "  <url>\n"
            f"    <loc>{SITE}/guides/{article['slug']}/</loc>\n"
            f"    <lastmod>{article['date'].isoformat()}</lastmod>\n"
            "  </url>"
        )
    if "\n</urlset>" not in text:
        die("sitemap.xml is missing </urlset>")
    text = text.replace("\n</urlset>", "\n" + "\n".join(blocks) + "\n</urlset>")
    if not text.endswith("\n"):
        text += "\n"
    SITEMAP.write_text(text, encoding="utf-8")


def main() -> None:
    entries = load_publish()
    articles = load_sources(entries)
    published = {article["slug"] for article in articles}
    if GUIDES_DIR.exists():
        shutil.rmtree(GUIDES_DIR)
    GUIDES_DIR.mkdir()
    for article in articles:
        write_article(article, published)
        print(f"wrote guides/{article['slug']}/index.html  {article['date'].isoformat()}")
    index_lastmod = write_index(articles)
    update_sitemap(articles, index_lastmod)
    print(f"wrote guides/index.html ({len(articles)} guides, newest first)")
    print("updated sitemap.xml")


if __name__ == "__main__":
    main()
