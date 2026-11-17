"""Draw the headline chart from out/results.json.

Usage: uv run python -m tts_id_bench.chart

Writes assets/results-light.svg and assets/results-dark.svg (one per GitHub theme).
"""

from __future__ import annotations

import json
from pathlib import Path

from .score import mean_cer
from .synth import VARIANTS

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "out" / "results.json"
ASSETS = ROOT / "assets"

THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "muted": "#52514e", "grid": "#e1e0d9", "raw": "#2a78d6", "normalized": "#eb6834"},
    "dark": {"surface": "#1a1a19", "ink": "#f0efec", "muted": "#c3c2b7", "grid": "#2c2c2a", "raw": "#3987e5", "normalized": "#d95926"},
}
LABELS = {"raw": "Raw text", "normalized": "Hand-normalized text"}

WIDTH, LEFT, RIGHT, TOP = 760, 170, 60, 86
BAR, GAP, GROUP_GAP = 14, 2, 22
FONT = "font-family=\"-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif\""


def bar(x: float, y: float, w: float, color: str) -> str:
    """Bar anchored to the baseline with a rounded data end."""
    w, r = max(w, 1.0), min(4.0, max(w, 1.0))
    return (
        f'<path d="M{x},{y} h{w - r:.1f} a{r},{r} 0 0 1 {r},{r} v{BAR - 2 * r} '
        f'a{r},{r} 0 0 1 -{r},{r} h-{w - r:.1f} z" fill="{color}"/>'
    )


def render(scores: list[tuple[str, dict[str, float]]], theme: dict[str, str]) -> str:
    plot_w = WIDTH - LEFT - RIGHT
    top = max(v for _, by_variant in scores for v in by_variant.values())
    axis_max = next(t for t in (5, 10, 15, 20, 30, 40, 50, 100) if t >= top * 100)
    group_h = len(VARIANTS) * BAR + (len(VARIANTS) - 1) * GAP
    height = TOP + len(scores) * (group_h + GROUP_GAP) + 30

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" height="{height}" role="img" '
        f'aria-label="Character error rate per engine on raw and hand-normalized Indonesian text">',
        f'<rect width="{WIDTH}" height="{height}" fill="{theme["surface"]}"/>',
        f'<text x="20" y="30" {FONT} font-size="16" font-weight="600" fill="{theme["ink"]}">'
        "Character error rate on Indonesian text, by engine</text>",
    ]
    # Legend, in the same order as the bars.
    x = 20
    for variant, label in LABELS.items():
        out.append(f'<rect x="{x}" y="46" width="10" height="10" rx="2" fill="{theme[variant]}"/>')
        out.append(f'<text x="{x + 16}" y="55" {FONT} font-size="12" fill="{theme["muted"]}">{label}</text>')
        x += 16 + len(label) * 6.6 + 24

    for tick in range(0, axis_max + 1, axis_max // 5):
        tx = LEFT + plot_w * tick / axis_max
        out.append(f'<line x1="{tx:.1f}" y1="{TOP - 8}" x2="{tx:.1f}" y2="{height - 30}" stroke="{theme["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{tx:.1f}" y="{height - 12}" {FONT} font-size="11" text-anchor="middle" fill="{theme["muted"]}">{tick}%</text>')

    for i, (engine, by_variant) in enumerate(scores):
        y = TOP + i * (group_h + GROUP_GAP)
        out.append(
            f'<text x="{LEFT - 12}" y="{y + group_h / 2 + 4:.1f}" {FONT} font-size="13" text-anchor="end" fill="{theme["ink"]}">{engine}</text>'
        )
        for j, variant in enumerate(VARIANTS):
            value = by_variant[variant]
            w = plot_w * value * 100 / axis_max
            by = y + j * (BAR + GAP)
            out.append(bar(LEFT, by, w, theme[variant]))
            out.append(
                f'<text x="{LEFT + max(w, 1) + 6:.1f}" y="{by + BAR - 3}" {FONT} font-size="12" fill="{theme["ink"]}">{value:.1%}</text>'
            )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    results = json.loads(RESULTS.read_text())
    scores = [
        (r["engine"], {v: mean_cer([x for x in r["sentences"] if x["variant"] == v]) for v in VARIANTS})
        for r in results
    ]
    scores.sort(key=lambda s: s[1]["raw"])
    ASSETS.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (ASSETS / f"results-{name}.svg").write_text(render(scores, theme))
        print(f"assets/results-{name}.svg")


if __name__ == "__main__":
    main()
