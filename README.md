# Deloitte Australia M&A Intelligence

A daily, evidence-led Australian M&A intelligence briefing designed for an Associate Director lens in Deloitte Strategy & Transactions / Consulting.

## What this agent does

Every morning at **7:05 am Australia/Sydney**, the GitHub Actions workflow:

1. Collects fresh Australian M&A signals from multiple Google News RSS searches, with targeted queries for Reuters, Deloitte, ACCC, ASX/company announcements and major Australian business media.
2. Deduplicates and ranks the source set.
3. Uses **GitHub Models** for synthesis, authenticated with the workflow's built-in `GITHUB_TOKEN`.
4. Produces a dated Markdown briefing in `briefings/YYYY-MM-DD.md`.
5. Optionally sends a concise, mobile-friendly version to Telegram.
6. Commits the briefing back to this repository.

The architecture is intentionally inspired by the modular research-ops approach used by the open-source [AI-News-Briefing](https://github.com/hoangsonww/AI-News-Briefing) project, but this repository is purpose-built for Australian M&A and the user's Deloitte AD lens rather than copied from it.

## Coverage

- Overall Australian M&A, not just mid-market
- Major corporate M&A
- Private equity: acquisitions, bolt-ons, portfolio value creation and exits
- Infrastructure, superannuation and sovereign capital
- Cross-border strategic buyers
- Resources and critical minerals
- Financial services
- TMT / technology
- Healthcare
- Energy / utilities / infrastructure
- Carve-outs, separations and divestitures
- Public-to-private and contested transactions
- ACCC / FIRB / regulatory developments
- Implications for Deloitte Strategy & Transactions / Consulting
- A daily **Deloitte AD lens**
- A daily **My Right-to-Play** section linked to banking, telecom, technology transformation, cloud/data/AI, enterprise architecture and large-scale integration experience

## Important design choices

### Evidence first
The model is instructed to distinguish confirmed facts from inference, avoid unsupported deal claims, and cite source IDs. The exact URLs gathered by the research stage are retained in every briefing.

### Whole-market lens
The agent deliberately avoids becoming a mid-market deal tracker. It prioritises transactions and strategic signals that could matter to major corporates, PE sponsors, infrastructure investors and Deloitte's senior client relationships.

### AI is not forced into the analysis
AI appears only when it is materially relevant to the transaction, operating model, technology, integration or value-creation thesis.

### Historical intelligence
Daily reports are committed to `briefings/`, creating a searchable M&A intelligence archive that can later support weekly/monthly trend analysis.

### Telegram delivery
The workflow can send the briefing to a Telegram chat using the official Telegram Bot API. The bot token and chat ID are stored as GitHub Actions repository secrets and are never committed to source code.

## Schedule

The workflow uses GitHub Actions' timezone-aware schedule with `Australia/Sydney`, so the 7:05 am run follows Sydney daylight-saving changes automatically. GitHub supports IANA timezone strings for scheduled workflows. See the [GitHub Actions schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule).

## Manual run

Open **Actions → Daily Deloitte Australia M&A Briefing → Run workflow**.

The workflow also supports a `lookback_days` input for deeper catch-up research.

## Telegram setup

Create a Telegram bot with BotFather, start a chat with the bot, and add these repository Actions secrets:

- `TELEGRAM_BOT_TOKEN` — the token issued by BotFather
- `TELEGRAM_CHAT_ID` — the chat/channel/group ID that should receive the briefing

The delivery step is optional: if either secret is absent, the research briefing still runs and is archived normally.

Telegram's Bot API `sendMessage` endpoint is used for delivery. Keep the bot token secret and do not place it in source files or workflow YAML.

## Model

The default model is configurable in the workflow environment. It currently uses `openai/gpt-4.1-mini` through GitHub Models. GitHub documents GitHub Models inference from GitHub Actions using the built-in `GITHUB_TOKEN` with `models: read` permission.

## Repository structure

```text
.
├── .github/workflows/daily-briefing.yml
├── config/sources.yaml
├── prompts/briefing.md
├── scripts/run_briefing.py
├── scripts/telegram_send.py
├── briefings/
├── requirements.txt
└── README.md
```

## Future extensions

- Weekly Partner briefing
- Sector heatmaps
- Deal database / structured JSON layer
- Account-level opportunity tracker
- PE sponsor / portfolio tracker
- Deloitte competitor intelligence
- Rich Telegram formatting and links
- Evaluation harness to score factuality, source quality, relevance and AD usefulness
