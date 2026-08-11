#!/usr/bin/env python3
"""Research -> synthesis -> dated Markdown briefing for Australian M&A."""
from __future__ import annotations

import datetime as dt
import email.utils
import html
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
    """Tiny parser for the intentionally simple project config; avoids a runtime dependency."""
    queries = []
    preferred = []
    section = None
    max_items = 8
    max_total = 70
    max_age = 7
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "queries:":
            section = "queries"; continue
        if line == "preferred_domains:":
            section = "preferred_domains"; continue
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
    req = urllib.request.Request(url, headers={"User-Agent": "Deloitte-AU-MNA-Intelligence/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read()
    root = ET.fromstring(data)
    items = []
    for item in root.findall("./channel/item")[:limit]:
        title = strip_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        description = strip_html(item.findtext("description", ""))
        pub = item.findtext("pubDate", "")
        try:
            published = email.utils.parsedate_to_datetime(pub).isoformat()
        except Exception:
            published = pub
        source_el = item.find("source")
        source = source_el.text.strip() if source_el is not None and source_el.text else "Google News"
        if title and link:
            items.append({"title": title, "url": link, "description": description[:900], "published": published, "source": source})
    return items


def dedupe(items: list[dict], max_total: int) -> list[dict]:
    seen = set()
    out = []
    for item in items:
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
    return dedupe(all_items, cfg["max_total"])


def build_context(items: list[dict]) -> str:
    chunks = []
    for i, item in enumerate(items, 1):
        chunks.append(
            f"[S{i}] {item['source']} | {item['published']}\n"
            f"TITLE: {item['title']}\nURL: {item['url']}\n"
            f"SUMMARY: {item['description']}"
        )
    return "\n\n".join(chunks)


def call_github_model(prompt: str, context: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not available")
    model = os.environ.get("GITHUB_MODEL", "openai/gpt-4.1-mini")
    system = open(PROMPT_PATH, encoding="utf-8").read()
    today = dt.datetime.now(ZoneInfo("Australia/Sydney")).strftime("%A, %d %B %Y")
    user = (
        f"Today is {today}.\n\n"
        "Research items follow. Use only these items as factual evidence.\n\n"
        + context
        + "\n\nGenerate the complete briefing now."
    )
    payload = (
        '{"model":' + json_quote(model) + ',"temperature":0.1,"max_tokens":7000,'
        '"messages":[{"role":"system","content":' + json_quote(system) + '},'
        '{"role":"user","content":' + json_quote(user) + '}]}'
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://models.github.ai/inference/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                import json
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("Model request failed")


def json_quote(value: str) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


def add_sources(report: str, items: list[dict]) -> str:
    source_lines = ["\n\n---\n\n## Research sources gathered"]
    for i, item in enumerate(items, 1):
        source_lines.append(f"- [S{i}] {item['source']} — {item['title']} — {item['published']} — {item['url']}")
    return report + "\n" + "\n".join(source_lines) + "\n"


def main() -> int:
    lookback = int(os.environ.get("LOOKBACK_DAYS", "7"))
    items = research(lookback)
    if not items:
        raise RuntimeError("No research items were collected")
    print(f"Collected {len(items)} research items")
    report = call_github_model("", build_context(items))
    report = add_sources(report, items)
    now = dt.datetime.now(ZoneInfo("Australia/Sydney"))
    date_str = now.strftime("%Y-%m-%d")
    out_dir = os.path.join(REPO_ROOT, "briefings")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date_str}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
