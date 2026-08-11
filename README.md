# Deloitte Australia M&A Intelligence

A daily, evidence-led Australian M&A intelligence briefing designed for an Associate Director lens in Deloitte Strategy & Transactions / Consulting.

## Architecture

This repository is the **research and persistent archive layer**. A GitHub Actions workflow runs the research agent at **6:45 am Australia/Sydney**, generates the day's briefing and commits it to `briefings/YYYY-MM-DD.md`.

A separate ChatGPT scheduled task is the **delivery layer** and delivers the completed briefing to the user at **7:00 am Australia/Sydney**. This avoids duplicate research and gives the user a clean morning experience while preserving a permanent GitHub archive.

```text
Australian M&A sources
        ↓
GitHub research + synthesis agent (06:45 Sydney)
        ↓
briefings/YYYY-MM-DD.md
        ↓
ChatGPT delivery task (07:00 Sydney)
        ↓
User's morning Deloitte AD briefing
```

The research architecture is intentionally inspired by the modular research-ops approach used by the open-source AI-News-Briefing project, but this repository is purpose-built for Australian M&A and the Deloitte AD lens rather than copied from it.

## What the agent covers

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

## Evidence-first design

The synthesis model is instructed to distinguish confirmed facts from inference, avoid unsupported deal claims, cite source IDs, and retain the exact URLs gathered by the research stage in every briefing.

The agent prioritises Reuters, Deloitte, ACCC, ASX/company announcements and high-quality Australian business reporting. It uses a seven-day research window but emphasises the last 24–48 hours.

## Whole-market lens

The agent deliberately avoids becoming a mid-market deal tracker. It prioritises developments that could matter to major corporates, PE sponsors, infrastructure investors, institutional capital and Deloitte's senior client relationships.

## AI is not forced into the analysis

AI appears only when it is materially relevant to the transaction, operating model, technology, integration or value-creation thesis.

## Historical intelligence

Daily reports are committed to `briefings/`, creating a searchable M&A intelligence archive that can later support weekly/monthly trend analysis, sector heatmaps, account tracking and sponsor tracking.

## Manual run

Open **Actions → Daily Deloitte Australia M&A Briefing → Run workflow**.

The workflow also supports a `lookback_days` input for deeper catch-up research.

## Model

The default model is configurable in the workflow environment. It currently uses `openai/gpt-4.1-mini` through GitHub Models, authenticated with the workflow's built-in `GITHUB_TOKEN` and `models: read` permission.

## Repository structure

```text
.
├── .github/workflows/daily-briefing.yml
├── config/sources.yaml
├── prompts/briefing.md
├── scripts/run_briefing.py
├── scripts/telegram_send.py       # optional legacy delivery utility; not used by the scheduled workflow
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
- Evaluation harness to score factuality, source quality, relevance and AD usefulness
