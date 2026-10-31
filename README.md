# Reading Feed

Public curated reading for Magnolia Works, RustJ lexical-tufte-css, and array compilers.

## Subscribe
Import [subscriptions.opml](subscriptions.opml) into NetNewsWire. Select either the combined feed or project feeds to avoid duplicates.

- https://yunskim.github.io/reading-feed/all.xml
- https://yunskim.github.io/reading-feed/magnolia.xml
- https://yunskim.github.io/reading-feed/rustj.xml
- https://yunskim.github.io/reading-feed/array-compilers.xml
- https://yunskim.github.io/reading-feed/lexical.xml
- https://yunskim.github.io/reading-feed/ssri-anatta.xml

## Publishing
Enable **Settings → Pages → Deploy from a branch → main → /docs**.

## Add articles
Edit `data/articles.json` (title, URL, projects, summary, insight, date; project key `array-compilers` for this topic). Push to main to generate RSS via GitHub Actions, or run `python scripts/build.py` locally.

## Daily automatic discovery

[Daily Reading Discovery](.github/workflows/daily.yml) runs daily at **09:15 KST** (00:15 UTC), or manually via Actions → Daily Reading Discovery → Run workflow. It searches public Hacker News results for four topics: Magnolia, RustJ, lexical-tufte-css, and array compilers. It filters by title relevance and community engagement, deduplicates original URLs, and limits additions to **3 per topic and 10 overall per day**. If no relevant articles qualify, the feeds do not change. It needs no API key.

**Editorial limitation:** this is deterministic keyword/engagement-based discovery, *not* an AI reading or evaluation of full articles. Auto-generated summaries explicitly say that the original needs review. Treat design implications as prompts for investigation, not verified conclusions. Manual entries can still be added to `data/articles.json`.

The workflow commits new entries and regenerated `docs/*.xml` to main; GitHub Pages publishes the resulting feeds. Failed external searches are reported; if every search fails, the workflow fails without overwriting the existing feed. Run `python -m unittest discover -s tests` to test discovery logic.

## SSRI, identity and anatta

The separate `ssri-anatta.xml` feed discovers Reddit discussions on antidepressants, changing sense of self, and Buddhist no-self. Search sources include r/Buddhism, r/secularbuddhism and r/lexapro. Titles and post bodies must contain both identity-related and antidepressant terms, using word boundaries. The subreddit name alone is not evidence of relevance. Each of the three subreddits is searched for both medication and identity terms. The script caps additions at five per run, deduplicates Reddit post IDs across hostnames, slugs and tracking parameters, and preserves existing articles when Reddit RSS is unavailable. It accepts posts from the last eight days, prefers the original published timestamp over edit time, rejects missing/invalid/naive/future dates, and emits the original publication date in RSS. Searches request the past week; there is no historical backfill. HTTP 403/429, timeouts, malformed XML and unexpected responses are logged as failures. A complete Reddit outage produces an Actions warning (not a misleading zero-match result); the other sources continue. If both HN and Reddit fail entirely, no data is written and the job fails. Discovery also runs on merges that change its code, tests or workflow. These are unverified personal accounts, not medical advice. Reddit may rate-limit or block automated requests.
