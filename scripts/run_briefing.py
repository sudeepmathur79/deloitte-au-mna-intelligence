#!/usr/bin/env python3
"""Research -> delta synthesis -> dated Markdown briefing for Australian M&A."""
from __future__ import annotations

import datetime as dt
import email.utils
import glob
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "sources.yaml")
PROMPT_PATH = os.path.join(REPO_ROOT, "prompts", "briefing.md")


def parse_simple_yaml(path: str) -> dict:
    queries, preferred = [], []
    section = None
    max_items, max_total, max_age = 8, 70, 7
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "queries:": section = "queries"; continue
        if line == "preferred_domains:": section = "preferred_domains"; continue
        if line.startswith("- "):
            value = line[2:].strip().strip("'\"")
            if section == "queries": queries.append(value)
            elif section == "preferred_domains": preferred.append(value)
            continue
        if ":" in line:
            key, value = [x.strip() for x in line.split(":", 1)]
            value = value.strip("'\"")
            if key == "max_items_per_query": max_items = int(value)
            elif key == "max_total_sources": max_total = int(value)
            elif key == "max_age_days": max_age = int(value)
    return {"queries": queries, "preferred_domains": preferred, "max_items": max_items, "max_total": max_total, "max_age": max_age}


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value or "", flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def fetch_rss(query: str, limit: int, lookback_days: int) -> list[dict]:
    q = f"{query} when:{lookback_days}d"
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-AU", "gl": "AU", "ceid": "AU:en"})
    req = urllib.request.Request(url, headers={"User-Agent": "Deloitte-AU-MNA-Intelligence/2.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        root = ET.fromstring(response.read())
    items = []
    for item in root.findall("./channel/item")[:limit]:
        title = strip_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        description = strip_html(item.findtext("description", ""))
        pub = item.findtext("pubDate", "")
        try:
            published = email.utils.parsedate_to_datetime(pub)
        except Exception:
            published = dt.datetime.now(dt.timezone.utc)
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else "Google News"
        if title and link:
            items.append({"title": title, "url": link, "description": description[:900], "published": published.isoformat(), "source": source})
    return items


def dedupe(items: list[dict], max_total: int, preferred: list[str]) -> list[dict]:
    seen, out = set(), []
    now = dt.datetime.now(dt.timezone.utc)
    def score(item):
        try:
            age = (now - dt.datetime.fromisoformat(item["published"]).astimezone(dt.timezone.utc)).total_seconds() / 86400
        except Exception:
            age = 7
        domain_bonus = 1 if any(d in item["url"] for d in preferred) else 0
        return domain_bonus * 100 - age
    for item in sorted(items, key=score, reverse=True):
        key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:max_total]


def research(lookback_days: int) -> list[dict]:
    cfg = parse_simple_yaml(CONFIG_PATH)
    all_items = []
    for query in cfg["queries"]:
        try:
            all_items.extend(fetch_rss(query, cfg["max_items"], lookback_days))
        except Exception as exc:
            print(f"WARN: query failed: {query}: {exc}", file=sys.stderr)
    return dedupe(all_items, cfg["max_total"], cfg["preferred_domains"])


def build_context(items: list[dict]) -> str:
    return "\n\n".join(
        f"[S{i}] {x['source']} | {x['published']}\nTITLE: {x['title']}\nURL: {x['url']}\nSUMMARY: {x['description']}"
        for i, x in enumerate(items, 1)
    )


def load_recent_briefings(limit: int = 3) -> str:
    files = sorted(glob.glob(os.path.join(REPO_ROOT, "briefings", "*.md")), reverse=True)[:limit]
    chunks = []
    for path in files:
        try:
            text = open(path, encoding="utf-8").read()
            chunks.append(f"--- PRIOR BRIEFING: {os.path.basename(path)} ---\n{text[:18000]}")
        except Exception as exc:
            print(f"WARN: prior briefing unavailable: {path}: {exc}", file=sys.stderr)
    return "\n\n".join(chunks)


def call_github_model(context: str, prior: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not available")
    model = os.environ.get("GITHUB_MODEL", "openai/gpt-4.1")
    system = open(PROMPT_PATH, encoding="utf-8").read()
    today = dt.datetime.now(ZoneInfo("Australia/Sydney")).strftime("%A, %d %B %Y")
    user = (
        f"Today is {today}.\n\nCURRENT RESEARCH ITEMS — these are the only factual evidence for today's events:\n\n{context}\n\n"
        "RECENT PRIOR BRIEFINGS — memory only, not new evidence. Use them to suppress repetition and identify changes.\n\n"
        + (prior or "No prior briefing available.")
        + "\n\nGenerate the complete DAILY DELTA briefing now. Novelty is more important than completeness."
    )
    payload = json.dumps({"model": model, "temperature": 0.1, "max_tokens": 7000, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://models.github.ai/inference/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("Model request failed")


def add_sources(report: str, items: list[dict]) -> str:
    lines = ["\n\n---\n\n## Research sources gathered"]
    for i, item in enumerate(items, 1):
        lines.append(f"- [S{i}] {item['source']} — {item['title']} — {item['published']} — {item['url']}")
    return report + "\n" + "\n".join(lines) + "\n"


def main() -> int:
    lookback = int(os.environ.get("LOOKBACK_DAYS", "7"))
    items = research(lookback)
    if not items:
        raise RuntimeError("No research items were collected")
    print(f"Collected {len(items)} research items")
    prior = load_recent_briefings(3)
    print(f"Loaded {prior.count('--- PRIOR BRIEFING:')} prior briefings for novelty comparison")
    report = add_sources(call_github_model(build_context(items), prior), items)
    date_str = dt.datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d")
    out_dir = os.path.join(REPO_ROOT, "briefings")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date_str}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
