#!/usr/bin/env python3
"""Daily topic-specific discovery from public Hacker News search, no API key."""
import json
import html
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/articles.json"
TOPICS = {
    "magnolia": {
        "queries": ["local-first software", "CRDT sync", "distributed version control"],
        "terms": ["local-first", "local first", "crdt", "sync", "offline-first", "distributed", "version control", "file sharing", "collaboration", "sqlite", "content addressed", "replication", "handoff"],
        "context": "Magnolia의 로컬 우선 데이터 소유권, 동기화, 파일 인계 및 버전 이력 설계와 비교",
    },
    "rustj": {
        "queries": ["array programming language", "J programming language", "egraph compiler"],
        "terms": ["array language", "array programming", "apl", "j language", "j programming", "egraph", "e-graph", "equality saturation", "autodiff", "automatic differentiation", "tensor compiler", "rank polymorphism"],
        "context": "RustJ의 배열 의미론, 프런트엔드, IR 및 최적화 규칙과 비교",
    },
    "lexical": {
        "queries": ["lexical editor", "rich text editor", "structured document editor"],
        "terms": ["lexical", "rich text", "rich-text", "prosemirror", "tiptap", "document editor", "editor architecture", "typography", "tufte", "contenteditable", "dom selection", "wysiwyg"],
        "context": "lexical-tufte-css의 구조화된 노드, DOM 표현, 편집 및 타이포그래피 설계와 비교",
    },
    "array-compilers": {
        "queries": ["tensor compiler", "array compiler", "MLIR linalg", "equality saturation"],
        "terms": ["tensor compiler", "array compiler", "mlir", "xla", "tvm", "triton", "halide", "polyhedral", "equality saturation", "e-graph", "egraph", "glenside", "tensat", "spores", "loop nest", "tensor optimization", "array programming"],
        "context": "배열·텐서 컴파일러의 IR, 변환 법칙 및 비용 기반 최적화 연구와 비교",
    },
}
API = "https://hn.algolia.com/api/v1/search_by_date"
USER_AGENT = "reading-feed/1.0 (public curated RSS)"

def normalize(url):
    p = urlsplit(url.strip())
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ValueError("Invalid URL")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", p.query, ""))

def fetch(query, since):
    params = urlencode({"query": query, "tags": "story", "numericFilters": f"created_at_i>{since}", "hitsPerPage": 50})
    req = Request(API + "?" + params, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=25) as response:
        return json.load(response)["hits"]

def match(title, terms):
    lower = title.lower()
    return [term for term in terms if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", lower)]

def discover(existing, now, fetcher=fetch):
    since = int((now - timedelta(days=3)).timestamp())
    known = {normalize(x["url"]) for x in existing}
    candidates = {}
    successes = 0
    for topic, config in TOPICS.items():
        for query in config["queries"]:
            try:
                hits = fetcher(query, since)
                successes += 1
            except Exception as exc:
                print(f"Source failed: {topic}/{query}: {exc}", file=sys.stderr)
                continue
            for hit in hits:
                title = (hit.get("title") or "").strip()
                url = hit.get("url") or ""
                if not title or not url or hit.get("created_at_i", 0) < since:
                    continue
                try:
                    key = normalize(url)
                except ValueError:
                    continue
                if key in known:
                    continue
                matched = match(title, config["terms"])
                if not matched:
                    continue
                # Require topical match in the title; avoid promoting tangential discussions.
                record = candidates.setdefault(key, {"title": title, "url": url, "projects": set(), "matched": {}, "points": 0, "comments": 0})
                record["projects"].add(topic)
                record["matched"][topic] = matched
                record["points"] = max(record["points"], int(hit.get("points") or 0))
                record["comments"] = max(record["comments"], int(hit.get("num_comments") or 0))
    if not successes:
        raise RuntimeError("All discovery queries failed; preserve existing feed")
    selected = sorted(candidates.values(), key=lambda x: (len(x["projects"]), x["points"] + x["comments"], x["title"]), reverse=True)
    limits = {topic: 0 for topic in TOPICS}
    added = []
    for item in selected:
        # Reject low-engagement noise; retain specialized research with some discussion.
        if item["points"] < 5 and item["comments"] < 3:
            continue
        projects = sorted(t for t in item["projects"] if limits[t] < 3)
        if not projects or len(added) >= 10:
            continue
        for topic in projects:
            limits[topic] += 1
        terms = sorted(set(sum((item["matched"][p] for p in projects), [])))
        added.append({
            "title": item["title"],
            "url": item["url"],
            "projects": projects,
            "summary": "Hacker News에서 발견한 관련 글. 제목의 주요 주제: " + ", ".join(terms[:5]) + ". 원문 확인 필요.",
            "insight": " / ".join(TOPICS[p]["context"] for p in projects),
            "added": now.date().isoformat(),
        })
    return added

REDDIT_SEARCHES = [
    (subreddit, query)
    for subreddit in ("Buddhism", "secularbuddhism", "lexapro")
    for query in ("SSRI OR antidepressant OR antidepressants OR lexapro OR escitalopram",
                  'identity OR personality OR anatta OR "no self" OR "sense of self"')
]
SELF_TERMS = ("self", "myself", "identity", "personality", "anatta", "anātman", "anatman", "no-self", "who am i", "ego", "자아", "무아")
MED_TERMS = ("ssri", "ssris", "lexapro", "antidepressant", "antidepressants", "prozac", "escitalopram", "sertraline", "zoloft", "약물", "항우울제")
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def reddit_key(url):
    """Canonical post identity, independent of host, title slug or tracking query."""
    p = urlsplit(url.strip())
    if p.scheme not in ("https", "http"):
        raise ValueError("Invalid Reddit URL")
    if p.hostname == "redd.it":
        post_id = p.path.strip("/")
    elif p.hostname in ("reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com", "np.reddit.com"):
        m = re.fullmatch(r"/r/[^/]+/comments/([a-z0-9]+)(?:/[^/]*)?/?", p.path, re.I)
        if not m:
            raise ValueError("Not a Reddit post")
        post_id = m.group(1)
    else:
        raise ValueError("Not Reddit")
    if not re.fullmatch(r"[a-z0-9]+", post_id, re.I):
        raise ValueError("Invalid post ID")
    return "https://www.reddit.com/comments/" + post_id.lower()


def fetch_reddit(subreddit, query):
    url = "https://www.reddit.com/r/" + subreddit + "/search.rss?" + urlencode(
        {"q": query, "restrict_sr": "1", "sort": "new", "t": "week", "limit": 100})
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=20) as response:
        root = ElementTree.fromstring(response.read())
    if root.tag != "{http://www.w3.org/2005/Atom}feed":
        raise ValueError("Expected Reddit Atom feed")
    return root


def discover_reddit(existing, now, fetcher=fetch_reddit):
    """Require medication AND identity in title/body; never infer medication from subreddit."""
    known = set()
    for article in existing:
        try:
            known.add(reddit_key(article["url"]))
        except ValueError:
            pass
    candidates, successes = {}, 0
    for subreddit, query in REDDIT_SEARCHES:
        try:
            root = fetcher(subreddit, query)
            if root.tag != "{http://www.w3.org/2005/Atom}feed":
                raise ValueError("Expected Reddit Atom feed")
            successes += 1
        except Exception as exc:
            print(f"Reddit RSS failed: {subreddit}/{query}: {exc}", file=sys.stderr)
            continue
        for entry in root.findall("a:entry", ATOM):
            title = entry.findtext("a:title", default="", namespaces=ATOM).strip()
            links = [x for x in entry.findall("a:link", ATOM) if x.get("rel", "alternate") == "alternate"]
            href = links[0].get("href", "") if links else ""
            # published is the creation date; updated may reflect an edit to an old post.
            published = entry.findtext("a:published", namespaces=ATOM)
            if published is None:
                published = entry.findtext("a:updated", default="", namespaces=ATOM)
            try:
                date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if date.tzinfo is None or not now - timedelta(days=8) <= date <= now:
                    continue
                date = date.astimezone(timezone.utc)
                key = reddit_key(href)
                path = urlsplit(href).path
                if not re.match(r"/r/" + re.escape(subreddit) + r"/comments/", path, re.I):
                    continue
            except (ValueError, TypeError):
                continue
            if not title or key in known:
                continue
            content = entry.findtext("a:content", default="", namespaces=ATOM)
            text = title + " " + html.unescape(re.sub(r"<[^>]*>", " ", content))
            if not match(text, SELF_TERMS) or not match(text, MED_TERMS):
                continue
            # Discard tracking parameters and fragments from emitted links too.
            clean = urlunsplit(("https", "www.reddit.com", path.rstrip("/") + "/", "", ""))
            candidates.setdefault(key, {
                "title": title, "url": clean, "projects": ["ssri-anatta"],
                "summary": "Reddit r/" + subreddit + "의 관련 토론. 게시글의 주장은 검증되지 않았으며 원문 확인 필요.",
                "insight": "항우울제·자아감 변화·불교의 무아와 수행의 관계를 살펴볼 사례. 의학적 근거로 취급하지 말 것.",
                "published": date.isoformat(), "added": now.date().isoformat(),
            })
    if not successes:
        raise RuntimeError("All Reddit feeds unavailable; existing entries preserved")
    added = sorted(candidates.values(), key=lambda x: (x["published"], x["url"]), reverse=True)[:5]
    print(f"Reddit RSS: {successes}/{len(REDDIT_SEARCHES)} searches succeeded; {len(added)} new posts")
    return added


def main():
    now = datetime.now(timezone.utc)
    existing = json.loads(DATA.read_text(encoding="utf-8"))
    additions, failures = [], []
    for source in (discover, discover_reddit):
        try:
            additions.extend(source(existing + additions, now))
        except RuntimeError as exc:
            failures.append(str(exc))
            print(f"::warning::{exc}", file=sys.stderr)
    if len(failures) == 2:
        raise RuntimeError("All sources failed; preserve existing data and feeds")
    if additions:
        DATA.write_text(json.dumps(existing + additions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added {len(additions)} articles")
    return len(additions)

if __name__ == "__main__":
    main()
