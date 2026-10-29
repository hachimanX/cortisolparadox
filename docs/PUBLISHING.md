# Publishing a guide

Article markdown lives in `_articles/`. GitHub Pages builds this site with Jekyll, which does not publish a folder whose name starts with `_`, so a file sitting there is not served as a page. Commit a source only when that article is published. Do not add a `.nojekyll` file; it would turn Jekyll off and could expose `_articles/`.

## Add the next article

1. Drop the markdown file into `_articles/`. Name it `slug.md` or `NN-slug.md` (a leading number and hyphen are stripped). The public URL is `/guides/<slug>/`.
2. The file must already contain these HTML comments, unchanged:

   ```html
   <!-- Meta title: ... -->
   <!-- Meta description: ... -->
   ```

3. Set its publish date by adding an entry at the end of `_articles/publish.json`:

   ```json
   {"slug": "your-slug", "date": "YYYY-MM-DD"}
   ```

   `date` is written into the page as `datePublished`. The guides index lists the newest date first. When two articles share a date, the one later in this file is treated as newer.

4. Build and check:

   ```bash
   python3 scripts/build_guides.py
   python3 scripts/check_links.py
   ```

5. Commit the new markdown file, `_articles/publish.json`, the generated files under `guides/`, and `sitemap.xml`.

A link written as `/guides/<slug>/` becomes a real link only when that slug is in `publish.json` and its source file is present. Otherwise the build writes `<span data-guide="slug">anchor text</span>` with no `href`. Run the build again after the target article is published and those spans become links.

The guides index and every published guide are added to `sitemap.xml`. Other sitemap URLs are left as they are.

## Batch scheduled for 2026-10-30

These five guides go out together the day after `wired-but-tired`. Their sources are not in the repo yet. Drop each file into `_articles/` under the name below (strip any upload suffix so the slug stays correct), then append these entries to the end of `_articles/publish.json`:

```json
{"slug": "how-to-calm-your-nervous-system", "date": "2026-10-30"},
{"slug": "dysregulated-nervous-system", "date": "2026-10-30"},
{"slug": "waking-up-at-3am-cortisol", "date": "2026-10-30"},
{"slug": "coffee-and-cortisol", "date": "2026-10-30"},
{"slug": "cortisol-face", "date": "2026-10-30"}
```

| Source file | Slug |
|---|---|
| `02-how-to-calm-your-nervous-system.md` | `how-to-calm-your-nervous-system` |
| `03-dysregulated-nervous-system.md` | `dysregulated-nervous-system` |
| `04-waking-up-at-3am-cortisol.md` | `waking-up-at-3am-cortisol` |
| `05-coffee-and-cortisol.md` | `coffee-and-cortisol` |
| `06-cortisol-face.md` | `cortisol-face` |

Then run:

```bash
python3 scripts/build_guides.py
python3 scripts/check_links.py
```

Commit the five markdown files, `_articles/publish.json`, `guides/`, and `sitemap.xml`. Rebuilding turns the placeholder spans in `wired-but-tired` that point at these five slugs into real links. The other nine guide targets stay spans until their own files are published.
