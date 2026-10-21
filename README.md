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
