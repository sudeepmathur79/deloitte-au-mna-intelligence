#!/usr/bin/env python3
"""Send the daily briefing to a Telegram chat using the Bot API."""
from __future__ import annotations

import datetime as dt
import html
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]


def clean_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.M)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def telegram_digest(report: str) -> str:
    sections = []
    wanted = [
        "Executive briefing",
        "Major transactions and live situations",
        "Deloitte opportunity map",
        "Deloitte AD lens — what I should know today",
        "My right-to-play",
        "What to watch next",
    ]
    for heading in wanted:
        pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
        match = re.search(pattern, report)
        if match:
            body = match.group(1).strip()
            if body:
                sections.append(f"{heading}\n{body}")
    if not sections:
        sections = [report]
    text = "\n\n".join(sections)
    text = clean_markdown(text)
    # Telegram Bot API sendMessage has a 4096-character text limit.
    limit = 3900
    if len(text) > limit:
        text = text[:limit].rsplit("\n", 1)[0].rstrip() + "\n\n… Full briefing is in the GitHub archive."
    today = dt.datetime.now(ZoneInfo("Australia/Sydney")).strftime("%d %b %Y")
    return f"🇦🇺 Deloitte AU M&A — {today}\n\n{text}"


def send_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8")
    if '"ok":true' not in body:
        raise RuntimeError(f"Telegram API error: {body[:500]}")


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram delivery not configured; skipping.")
        return 0

    date_str = dt.datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d")
    report_path = REPO_ROOT / "briefings" / f"{date_str}.md"
    if not report_path.exists():
        raise FileNotFoundError(report_path)

    report = report_path.read_text(encoding="utf-8")
    send_message(token, chat_id, telegram_digest(report))
    print("Telegram briefing delivered successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
