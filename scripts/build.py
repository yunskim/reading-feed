#!/usr/bin/env python3
"""Build curated RSS feeds from data/articles.json using the standard library."""
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from xml.etree.ElementTree import Element, SubElement, ElementTree

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://yunskim.github.io/reading-feed"
PROJECTS = {"magnolia": "Magnolia Works", "rustj": "RustJ", "array-compilers": "Array Compilers", "lexical": "lexical-tufte-css"}

def normalized(url):
    parts = urlsplit(url.strip())
    if parts.scheme not in ("https", "http") or not parts.netloc:
        raise ValueError(f"Invalid article URL: {url}")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", parts.query, ""))

def write_feed(path, title, entries):
    rss = Element("rss", {"version": "2.0"})
    channel = SubElement(rss, "channel")
    for tag, value in (("title", title), ("link", BASE + "/"), ("description", "Selected reading for thoughtful software design"), ("language", "ko")):
        SubElement(channel, tag).text = value
    for article in entries:
        item = SubElement(channel, "item")
        for tag, value in (("title", article["title"]), ("link", article["url"]), ("guid", normalized(article["url"])), ("description", article["summary"] + "\n\n설계 시사점: " + article["insight"])):
            SubElement(item, tag, {"isPermaLink": "false"} if tag == "guid" else {}).text = value
        dt = datetime.fromisoformat(article["added"]).replace(tzinfo=timezone.utc)
        SubElement(item, "pubDate").text = format_datetime(dt)
    path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(rss).write(path, encoding="utf-8", xml_declaration=True)

def main():
    articles = json.loads((ROOT / "data/articles.json").read_text(encoding="utf-8"))
    seen = set()
    for article in articles:
        key = normalized(article["url"])
        if key in seen:
            raise ValueError(f"Duplicate article: {key}")
        seen.add(key)
        if not article.get("title") or not article.get("summary") or not article.get("insight"):
            raise ValueError("Missing required article fields")
        if not article.get("projects") or set(article["projects"]) - set(PROJECTS):
            raise ValueError(f"Unknown project: {article['projects']}")
        datetime.fromisoformat(article["added"])
    articles.sort(key=lambda x: (x["added"], x["title"]), reverse=True)
    for key, name in PROJECTS.items():
        write_feed(ROOT / "docs" / f"{key}.xml", f"Reading Feed — {name}", [a for a in articles if key in a["projects"]])
    write_feed(ROOT / "docs" / "all.xml", "Reading Feed — All Projects", articles)
    (ROOT / "docs" / ".nojekyll").touch()

if __name__ == "__main__":
    main()
