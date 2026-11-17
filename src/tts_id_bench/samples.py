"""Export a few clips and build the listening page served by GitHub Pages.

Usage: uv run python -m tts_id_bench.samples

Writes docs/samples/<engine>/<variant>/<id>.mp3 and docs/index.html. Needs ffmpeg.
"""

from __future__ import annotations

import html
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
DOCS = ROOT / "docs"
REPO_URL = "https://github.com/rmaw22/tts-id-bench"

# One sentence per failure pattern, plus a plain one as the control.
SAMPLE_IDS = ["plain-02", "currency-02", "datetime-02", "unit-01", "abbrev-03", "informal-02"]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>tts-id-bench: audio samples</title>
<style>
  :root {{ --bg: #fcfcfb; --ink: #0b0b0b; --muted: #52514e; --line: #e1e0d9; --card: #ffffff; --bad: #b3261e; --good: #0a7a0a; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #1a1a19; --ink: #f0efec; --muted: #c3c2b7; --line: #2c2c2a; --card: #222221; --bad: #f08a80; --good: #6fcf6f; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 32px 16px 64px; background: var(--bg); color: var(--ink);
         font: 15px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
  main {{ max-width: 980px; margin: 0 auto; }}
  h1 {{ font-size: 24px; margin: 0 0 8px; }}
  h2 {{ font-size: 17px; margin: 40px 0 4px; }}
  p {{ margin: 0 0 12px; color: var(--muted); max-width: 70ch; }}
  a {{ color: inherit; }}
  .text {{ color: var(--ink); font-weight: 500; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 12px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }}
  .engine {{ font-weight: 600; font-size: 13px; }}
  .variant {{ font-size: 12px; color: var(--muted); margin-top: 10px; }}
  .heard {{ font-size: 12px; color: var(--muted); margin: 4px 0 0; overflow-wrap: anywhere; }}
  .cer {{ font-variant-numeric: tabular-nums; }}
  .cer.bad {{ color: var(--bad); }} .cer.good {{ color: var(--good); }}
  audio {{ width: 100%; height: 32px; margin-top: 4px; }}
</style>
</head>
<body>
<main>
<h1>tts-id-bench: audio samples</h1>
<p>Machine-generated speech from four open-weight text-to-speech models reading Indonesian text.
Each card has the clip for the raw text and for the hand-normalized text, the character error rate,
and what the literal speech recognizer heard. Full results and method:
<a href="{repo}">{repo}</a>.</p>
{sections}
</main>
</body>
</html>
"""


def main() -> None:
    results = json.loads((OUT / "results.json").read_text())
    sentences = {s["id"]: s for s in json.loads((ROOT / "data" / "sentences.json").read_text())}

    sections = []
    for sid in SAMPLE_IDS:
        s = sentences[sid]
        variants = ["raw"] + (["normalized"] if s["normalized"] != s["text"] else [])
        cards = []
        for r in results:
            parts = [f'<div class="engine">{html.escape(r["engine"])}</div>']
            for variant in variants:
                row = next(x for x in r["sentences"] if x["id"] == sid and x["variant"] == variant)
                rel = Path("samples") / r["engine"] / variant / f"{sid}.mp3"
                (DOCS / rel).parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / r["engine"] / variant / f"{sid}.wav"),
                     "-ac", "1", "-b:a", "64k", str(DOCS / rel)],
                    check=True,
                )
                grade = "good" if row["cer"] < 0.05 else "bad"
                parts.append(
                    f'<div class="variant">{variant} · <span class="cer {grade}">{row["cer"]:.0%} error</span></div>'
                    f'<audio controls preload="none" src="{rel.as_posix()}"></audio>'
                    f'<p class="heard">heard: {html.escape(row["heard"]["literal"])}</p>'
                )
            cards.append(f'<div class="card">{"".join(parts)}</div>')
        normalized = (
            f'<p>Normalized: <span class="text">{html.escape(s["normalized"])}</span></p>' if len(variants) > 1 else ""
        )
        sections.append(
            f'<h2>{html.escape(s["category"])}</h2>'
            f'<p>Raw: <span class="text">{html.escape(s["text"])}</span></p>{normalized}'
            f'<div class="grid">{"".join(cards)}</div>'
        )

    (DOCS / "index.html").write_text(PAGE.format(repo=REPO_URL, sections="\n".join(sections)))
    print(f"docs/index.html, {len(list(DOCS.rglob('*.mp3')))} clips")


if __name__ == "__main__":
    main()
