# Daily goalie bot

Runs every day at midnight US Eastern (`.github/workflows/daily-goalie-bot.yml`).

1. **MoneyPuck stats** (`fetch_moneypuck.py`): downloads the current season's goalie CSV
   from MoneyPuck's data page and saves it to `data/moneypuck/goalies_<season>.csv`, plus
   `data/moneypuck/summary.json` with a goals-saved-above-expected leaderboard.
2. **News digest** (`news_digest.py`): Claude searches the web for goalie injuries, recalls,
   emergency recalls, waivers, contracts and cap news, and writes `news/<date>.md`
   (and `news/latest.md`) with source links.

The results are committed to `main` by the workflow. Git history keeps every day's data.

## Setup

Add an Anthropic API key as a repository secret named `ANTHROPIC_API_KEY`
(Settings > Secrets and variables > Actions). To test without waiting for midnight,
open the Actions tab, pick "Daily Goalie Bot" and press "Run workflow".

## MoneyPuck terms

MoneyPuck's data is free for non-commercial use and must be credited wherever it is shown
("Data courtesy of MoneyPuck.com"). Commercial use needs their permission; see
https://moneypuck.com/data.htm. The bot only downloads the published CSV, once a day.
