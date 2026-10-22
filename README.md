# Reading Feed

Public curated reading for Magnolia Works, RustJ lexical-tufte-css, and array compilers.

## Subscribe
Import [subscriptions.opml](subscriptions.opml) into NetNewsWire. Select either the combined feed or project feeds to avoid duplicates.

- https://yunskim.github.io/reading-feed/all.xml
- https://yunskim.github.io/reading-feed/magnolia.xml
- https://yunskim.github.io/reading-feed/rustj.xml
- https://yunskim.github.io/reading-feed/array-compilers.xml
- https://yunskim.github.io/reading-feed/lexical.xml

## Publishing
Enable **Settings → Pages → Deploy from a branch → main → /docs**.

## Add articles
Edit `data/articles.json` (title, URL, projects, summary, insight, date; project key `array-compilers` for this topic). Push to main to generate RSS via GitHub Actions, or run `python scripts/build.py` locally.

## Daily automatic discovery

[Daily Reading Discovery](.github/workflows/daily.yml) runs daily at **09:15 KST** (00:15 UTC), or manually via Actions → Daily Reading Discovery → Run workflow. It searches public Hacker News results for four topics: Magnolia, RustJ, lexical-tufte-css, and array compilers. It filters by title relevance and community engagement, deduplicates original URLs, and limits additions to **3 per topic and 10 overall per day**. If no relevant articles qualify, the feeds do not change. It needs no API key.

**Editorial limitation:** this is deterministic keyword/engagement-based discovery, *not* an AI reading or evaluation of full articles. Auto-generated summaries explicitly say that the original needs review. Treat design implications as prompts for investigation, not verified conclusions. Manual entries can still be added to `data/articles.json`.

The workflow commits new entries and regenerated `docs/*.xml` to main; GitHub Pages publishes the resulting feeds. Failed external searches are reported; if every search fails, the workflow fails without overwriting the existing feed. Run `python -m unittest discover -s tests` to test discovery logic.
