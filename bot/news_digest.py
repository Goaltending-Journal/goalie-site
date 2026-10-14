"""Write a daily NHL goaltending news digest to news/YYYY-MM-DD.md using Claude with web search.

Needs the ANTHROPIC_API_KEY repository secret.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

NEWS_DIR = Path(__file__).resolve().parent.parent / "news"
EASTERN = ZoneInfo("America/New_York")
MODEL = "claude-opus-5-5"
MAX_CONTINUATIONS = 5

SYSTEM = """You are the news researcher for Goaltending Journal, a site about NHL goaltenders.
Search the web for NHL goaltending news from the last 24 hours and write a digest in Markdown.

Cover, in this order, with a "## " heading for each section:
1. Injuries: new injuries, injured reserve and LTIR moves, return timelines, goalies cleared to play.
2. Recalls and assignments: AHL/ECHL recalls and reassignments, emergency recalls, emergency backup goalies (EBUGs), waivers and claims.
3. Contracts and salary cap: signings, extensions, trades, buyouts, terminations, and how they affect each team's cap.
4. Other news: notable starts, milestones, coaching changes, and anything else a goalie-focused reader would want.

Rules:
- Only report items you found in a source today. Never guess or fill gaps from memory.
- One bullet per item: bold the goalie's name, then the team, what happened, and the source link.
- Include cap hits and contract terms only when a source states them.
- If a section has nothing new, write "Nothing new today."
- Skip items already in yesterday's digest unless there is a new development.
- Reply with only the digest, starting with the first "## " heading."""


def run(client: anthropic.Anthropic, prompt: str) -> anthropic.types.beta.BetaMessage:
    messages = [{"role": "user", "content": prompt}]
    for _ in range(MAX_CONTINUATIONS + 1):
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=32000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 20}],
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason != "pause_turn":
            return response
        # Server-side search loop paused; send the turn back and it resumes.
        messages = [messages[0], {"role": "assistant", "content": response.content}]
    return response


def main() -> int:
    today = datetime.now(EASTERN).date()
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    yesterday_file = NEWS_DIR / f"{today - timedelta(days=1)}.md"
    yesterday = yesterday_file.read_text(encoding="utf-8") if yesterday_file.exists() else "(none)"

    prompt = (
        f"Today is {today:%A, %B %-d, %Y} (US Eastern). Write today's goaltending digest.\n\n"
        f"<yesterdays_digest>\n{yesterday}\n</yesterdays_digest>"
    )
    response = run(anthropic.Anthropic(), prompt)

    if response.stop_reason == "refusal":
        print(f"Request declined: {response.stop_details}", file=sys.stderr)
        return 1

    body = "".join(b.text for b in response.content if b.type == "text").strip()
    if not body:
        print(f"No digest text returned (stop_reason={response.stop_reason})", file=sys.stderr)
        return 1

    sources = {}
    for block in response.content:
        if block.type == "text":
            for c in block.citations or []:
                url = getattr(c, "url", None)
                if url:
                    sources.setdefault(url, getattr(c, "title", None) or url)

    lines = [f"# Goaltending news: {today:%B %-d, %Y}", "", body, ""]
    if sources:
        lines += ["## Sources", ""] + [f"- [{t}]({u})" for u, t in sources.items()] + [""]
    text = "\n".join(lines)

    (NEWS_DIR / f"{today}.md").write_text(text, encoding="utf-8")
    (NEWS_DIR / "latest.md").write_text(text, encoding="utf-8")
    print(f"Wrote news/{today}.md ({len(sources)} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
